import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db import get_connection

conn = get_connection()

script_dir = os.path.dirname(os.path.abspath(__file__))
schema_path = os.path.join(script_dir, "schema.sql")

with open(schema_path, "r") as f:
    sql_script = f.read()

for statement in sql_script.split(";"):
    statement = statement.strip()
    if statement:
        conn.execute(statement)

print("Schema created successfully.")

tables = conn.execute("SELECT table_name FROM EXA_ALL_TABLES WHERE table_schema = 'DECISIONGUARD'").fetchall()
print("Tables:", tables)
