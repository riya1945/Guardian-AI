import pyexasol
from dotenv import load_dotenv
import os

load_dotenv()

def get_connection():
    """Single source of truth for connecting to Exasol. Used by guardrail, API, and scripts."""
    conn = pyexasol.connect(
        dsn=f"{os.getenv('EXASOL_HOST')}/nocertcheck:{os.getenv('EXASOL_PORT')}",
        user=os.getenv('EXASOL_USER'),
        password=os.getenv('EXASOL_PASSWORD')
    )
    conn.execute("CREATE SCHEMA IF NOT EXISTS decisionguard")
    conn.execute("OPEN SCHEMA decisionguard")
    return conn
