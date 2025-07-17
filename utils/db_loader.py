from langchain_community.utilities import SQLDatabase
from utils.config_loader import load_config

def load_db():
    db = None
    config = load_config()
    db_details = config["database"]
    db = SQLDatabase.from_uri(
        f"{db_details['dialect']}://{db_details['user']}:{db_details['password']}@{db_details['host']}:{db_details['port']}/{db_details['db_name']}"
    )

    return db
    

if __name__ == "__main__":
    print(load_db())