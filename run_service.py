from langchain_groq import ChatGroq
from database.db_connection_via_langchain import get_sql_database
from tools.get_tools import get_sql_tools, create_db_query_tool
from langchain_core.prompts import ChatPromptTemplate
from pydantic.pydantic_classes import SubmitFinalAnswer

from prompt_library.prompts import query_check_system, query_gen_system

llm = ChatGroq(model = "deepseek-r1-distill-llama-70b")
db = get_sql_database(
    dialect="postgresql",
    user="postgres",
    password="mysecretpassword",
    host="localhost",
    port=5432,
    db_name="testdb"
)

tools, list_tables_tool, get_schema_tool = get_sql_tools(db=db, llm=llm)
db_query_tool = create_db_query_tool(db)

query_check_prompt = ChatPromptTemplate.from_messages([("system", query_check_system), ("placeholder", "{messages}")])
query_check = query_check_prompt | llm.bind_tools([db_query_tool])

query_gen_prompt = ChatPromptTemplate.from_messages([("system", query_gen_system), ("placeholder", "{messages}")])
query_gen = query_gen_prompt | llm.bind_tools([SubmitFinalAnswer])

if __name__ == "__main__":
    # print(db_query_tool.invoke("SELECT * FROM invoices LIMIT 10;"))
    response = query_check.invoke({"messages": [("user", "SELECT * FROM invoices LIMIT 5;")]})
    print(response)
    print(response.tool_calls)


