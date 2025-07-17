from langchain_community.utilities import SQLDatabase

def get_sql_database(dialect, user, password, host, port, db_name):
    """
    Creates a LangChain SQLDatabase connection dynamically.

    Args:
        dialect (str): e.g., "postgresql", "mysql", etc.
        user (str): Database username.
        password (str): Database password.
        host (str): Hostname or IP address.
        port (str/int): Port number.
        db_name (str): Database name.

    Returns:
        SQLDatabase: LangChain-compatible database object.
    """
    uri = f"{dialect}://{user}:{password}@{host}:{port}/{db_name}"
    return SQLDatabase.from_uri(uri)


if __name__ == "__main__": 
    try:
        # Example usage
        db = get_sql_database(
            dialect="postgresql",
            user="postgres",
            password="mysecretpassword",
            host="localhost",
            port=5432,
            db_name="testdb"
        )

    
        print("Dialect:", db.dialect)
        print("Usable tables:", db.get_usable_table_names())
    except Exception as error: 
        print("Error while connecting to database --> ", error)