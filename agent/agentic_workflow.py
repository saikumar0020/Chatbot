from typing import Annotated, Literal
from langchain_core.messages import AIMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import AnyMessage, add_messages
from typing import Any
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda, RunnableWithFallbacks
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate

from prompt_library.prompts import query_gen_system_prompt, query_check_system_prompt
from utils.model_loader import load_llm
from utils.db_loader import load_db
from tools.get_tools import create_db_query_tool, get_sql_tools
from langgraph.types import Command
from prompt_library.prompts import supervisor_system_prompt
from typing import Literal
from typing_extensions import TypedDict

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class SubmitFinalAnswer(BaseModel):
    """Submit the final answer to the user based on the query results."""
    final_answer: str = Field(..., description="The final answer to the user")

class Router(TypedDict): 
    next: Literal["list_tables_and_schema", "general_response"]

class GraphBuilder(): 

    def __init__(self, model_provider: str = 'groq'): 
        self.llm = load_llm(provider = model_provider)
        self.db = load_db()
        self.graph = None

    def supervisor_node(self, state: State) -> Command[Literal["list_tables_and_schema", "general_response"]]:
        try:
            messages = [{"role": "system", "content": supervisor_system_prompt}] + state["messages"]
            
            llm_with_structure_output = self.llm.with_structured_output(Router)
            response = llm_with_structure_output.invoke(messages)
            goto = response["next"]
            print("*****************BELOW IS MY GOTO **************")
            print(goto)

            return Command(goto = goto, update = {"next": goto})
        except Exception as error: 
            print("Error from supervisor_node --> ", error)

    def general_response_node(self, state: State) -> dict[str, list[AIMessage]]:
        try:
            user_message = state["messages"][-1].content
            print("User message from GR --> ", user_message)
            response = self.llm.invoke(user_message)

            # Extract string content if response is an object
            if hasattr(response, "content"):
                content = response.content
            elif isinstance(response, dict) and "content" in response:
                content = response["content"]
            else:
                content = str(response)

            # Remove <think> and </think> tags
            cleaned_content = content.replace("<think>", "").replace("</think>", "").strip()
            print("Response from GR --> ", cleaned_content)
            return {"messages": [AIMessage(content=cleaned_content)]}

        except Exception as error:
            print("Error from general_response_node --> ", error)

    
    def list_tables_and_schema_call(self, state: State) -> dict[str, list[AIMessage]]:
        try:
            # Call list tables tool first
            list_tables_tool = next((tool for tool in get_sql_tools(self.db, self.llm)[0] if tool.name == "sql_db_list_tables"), None)
            get_schema_tool = next((tool for tool in get_sql_tools(self.db, self.llm)[0] if tool.name == "sql_db_schema"), None)
            if not list_tables_tool or not get_schema_tool:
                return {"messages": [AIMessage(content="Error: Required tools not found.", tool_calls=[])]}
            # Get table names
            table_names_output = list_tables_tool.invoke({"tool_input": ""})
            table_names = [name.strip() for name in table_names_output.split(",") if name.strip()]
            # Prepare tool calls for schema of each table
            tool_calls = [
                {"name": "sql_db_schema", "args": {"table_names": table}, "id": f"tool_schema_{table}"}
                for table in table_names
            ]
            print("Tool calls --> ", tool_calls)
            return {"messages": [AIMessage(content="", tool_calls=tool_calls)]}    
        except Exception as error: 
            print("Error in list_tables_and_schema_call --> ", error)

    
    # Generates fallback error messages for failed tool calls
    # To catch tool execution errors and return a structured error message back to the agent (LLM).
    def handle_tool_error(self, state:State) -> dict:
        try:
            error = state.get("error") 
            tool_calls = state["messages"][-1].tool_calls
            return {
                "messages": [
                ToolMessage(content=f"Error: {repr(error)}\n please fix your mistakes.",tool_call_id=tc["id"],)
                for tc in tool_calls
                ]
            }
        except Exception as error:
            print("Error in handle_tool_error --> ", error)

    # Creates a tool executor with automatic error handling
    # To create ToolNode, with a fallback mechanism using handle_tool_error, if something fails. 
    # Input --> tools 

    # Output 
    # --> ToolNode if no issue (error) 
    # --> If it fails (due to exception), if fall back to handle_tool_error with exception_key as error. 
    def create_tool_node_with_fallback(self, tools: list) -> RunnableWithFallbacks[Any, dict]:
        try:
            return ToolNode(tools).with_fallbacks([RunnableLambda(self.handle_tool_error)], exception_key="error")
        except Exception as error:
            print("Error in create_tool_node_with_fallback --> ", error)


    # Node 
    def query_gen_node(self, state: State):
        try:
            query_gen_prompt = ChatPromptTemplate.from_messages([("system", query_gen_system_prompt), ("placeholder", "{messages}")])

            query_gen = query_gen_prompt | self.llm.bind_tools([SubmitFinalAnswer])

            message = query_gen.invoke(state)

            # Sometimes, the LLM will hallucinate and call the wrong tool. We need to catch this and return an error message.
            tool_messages = []

            # If the message is just SQL (not a tool call), execute it
            if not getattr(message, "tool_calls", None) and "select" in message.content.lower():
                db_query_tool = create_db_query_tool(self.db)
                result = db_query_tool.invoke(message.content)
                # Wrap result as a message
                message.content += f"\n\nQuery Result:\n{result}"

            if message.tool_calls:
                for tc in message.tool_calls:
                    if tc["name"] != "SubmitFinalAnswer":
                        tool_messages.append(
                            ToolMessage(
                                content=f"Error: The wrong tool was called: {tc['name']}. Please fix your mistakes. Remember to only call SubmitFinalAnswer to submit the final answer. Generated queries should be outputted WITHOUT a tool call.",
                                tool_call_id=tc["id"],
                            )
                        )
            else:
                tool_messages = []
            return {"messages": [message] + tool_messages} 
        except Exception as error:
            print("Error in query_gen_node --> ", error)
    

    # Router for conditional edge 
    def should_continue(self, state: State) -> Literal[END, "correct_query", "query_gen"]:
        try:
            messages = state["messages"]
            last_message = messages[-1]
            if getattr(last_message, "tool_calls", None):
                return END
            if last_message.content.startswith("Error:"):
                return "query_gen"
            else:
                return "correct_query"
        except Exception as error:
            print("Error in should_continue --> ", error)
    
    # Node 
    def model_check_query(self, state: State) -> dict[str, list[AIMessage]]:
        """
        Use this tool to double-check if your query is correct before executing it.
                """
        try:
            db_query_tool = create_db_query_tool(self.db)

            query_check_prompt = ChatPromptTemplate.from_messages([("system", query_check_system_prompt), 
                                                                ("placeholder", "{messages}")])

            query_check = query_check_prompt | self.llm.bind_tools([db_query_tool])

            return {"messages": [query_check.invoke({"messages": [state["messages"][-1]]})]}    
        except Exception as error:
            print("Error in model_check_query --> ", error)


    def build_graph(self):
        try: 

            tools, list_tables_tool, get_schema_tool = get_sql_tools(self.db, self.llm)
            db_query_tool = create_db_query_tool(self.db)
            
            graph_builder = StateGraph(State)
            graph_builder.add_node("supervisor", self.supervisor_node)
            graph_builder.add_node("general_response", self.general_response_node)        
            graph_builder.add_node("list_tables_and_schema", self.list_tables_and_schema_call)
            graph_builder.add_node("get_schema_tool", self.create_tool_node_with_fallback([get_schema_tool]))
            graph_builder.add_node("query_gen", self.query_gen_node)
            graph_builder.add_node("correct_query", self.model_check_query)
            graph_builder.add_node("execute_query", self.create_tool_node_with_fallback([db_query_tool]))

            graph_builder.add_edge(START, "supervisor")
            graph_builder.add_edge("list_tables_and_schema", "get_schema_tool")
            graph_builder.add_edge("get_schema_tool", "query_gen")
            graph_builder.add_conditional_edges("query_gen", self.should_continue)
            graph_builder.add_edge("correct_query", "execute_query")
            graph_builder.add_edge("execute_query", "query_gen")

            self.graph = graph_builder.compile()
            return self.graph
        except Exception as error:
            print("Error in build_graph --> ", error)

    def __call__(self):
        return self.build_graph()