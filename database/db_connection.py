from sqlalchemy import create_engine, text

# Create PostgreSQL engine
engine = create_engine("postgresql://postgres:mysecretpassword@localhost:5432/testdb")


def run_sql(query: str) -> str:
    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.fetchall()
        return str(rows)

if __name__ == "__main__": 
    try:
        print(run_sql("SELECT * FROM invoices LIMIT 10;"))
    except Exception as error: 
        print("Error while running query --> ", error)