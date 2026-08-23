import pyexasol
from dotenv import load_dotenv
import os

load_dotenv()

conn = pyexasol.connect(
    dsn=f"{os.getenv('EXASOL_HOST')}/nocertcheck:{os.getenv('EXASOL_PORT')}",
    user=os.getenv('EXASOL_USER'),
    password=os.getenv('EXASOL_PASSWORD')
)

print(conn.execute("SELECT 1").fetchall())