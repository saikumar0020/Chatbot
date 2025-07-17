from langchain_core.tools import tool
from langchain_community.utilities import SQLDatabase

from langchain_community.agent_toolkits import SQLDatabaseToolkit

def get_sql_tools(db, llm):
    """
    Creates a SQLDatabaseToolkit from the given db and llm, prints all tool names,
    and returns the toolkit's tools along with the list tables and schema tools.

    Args:
        db: The SQLDatabase object (from langchain_community.utilities.SQLDatabase).
        llm: The language model instance to be used with the toolkit.

    Returns:
        tuple: (tools, list_tables_tool, get_schema_tool)
            - tools: List of all tools from the toolkit.
            - list_tables_tool: The tool for listing database tables.
            - get_schema_tool: The tool for retrieving a table's schema.
    """
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()

    # # Print the name of every tool for debugging
    # for tool in tools:
    #     print(tool.name)

    # Find the tools of interest by their name.
    list_tables_tool = next((tool for tool in tools if tool.name == "sql_db_list_tables"), None)
    get_schema_tool = next((tool for tool in tools if tool.name == "sql_db_schema"), None)

    return tools, list_tables_tool, get_schema_tool

# Tool factory function 
# create a tool dynamically using a closure:
def create_db_query_tool(db: SQLDatabase):
    @tool
    def db_query_tool(query: str) -> str:
        """
        Execute a SQL query against the database and return the result.
        If the query is invalid or returns no result, an error message will be returned.
        In case of an error, the user is advised to rewrite the query and try again.
        """
        result = db.run_no_throw(query)
        if not result:
            return "Error: Query failed. Please rewrite your query and try again."
        return result
    return db_query_tool


@tool
def user_query_validation(query: str) -> str:
    """Validates and improves user input before processing."""
    # Could use LLM to rephrase or clarify
    return query






