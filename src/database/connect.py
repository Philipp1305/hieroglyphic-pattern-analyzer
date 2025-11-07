import psycopg2
from dataclasses import dataclass
from os import getenv
from pathlib import Path

def connect():
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except Exception:
        pass

    @dataclass(frozen=True)
    class LoginCredentials:
        db_user: str = getenv("DB_USER", "")
        db_pass: str = getenv("DB_PASS", "")
        db_host: str = getenv("DB_HOST", "")
        db_port: int = int(getenv("DB_PORT", ""))
        db_name: str = getenv("DB_NAME", "")

        def validate(self) -> None:
            missing = [k for k, v in vars(self).items() if not str(v)]
            if missing:
                raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    return psycopg2.connect(
        host        = LoginCredentials.db_host,
        port        = LoginCredentials.db_port,
        database    = LoginCredentials.db_name,
        user        = LoginCredentials.db_user, 
        password    = LoginCredentials.db_pass
    )


def test_connection() -> bool:
    """
    Try to establish a connection and run a cheap query.

    Returns True on success, otherwise False.
    """
    conn = None
    try:
        conn = connect()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return True
    except Exception as exc:
        print(f"Database connection test failed: {exc}")
        return False
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    test = test_connection()
    if test == True:
        print("Database connection successful.")
    else:
        print("Database connection failed.")