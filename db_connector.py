"""Database connector utility.

Reads DB credentials from .env and exposes:
 - get_conn(dbname=None) -> mysql.connector connection
 - cursor() context manager yielding a cursor
 - test_connection() entrypoint for quick verification

Run this file directly to test the connection (it will print DB and MySQL version).
"""
import os
import traceback
from contextlib import contextmanager

from dotenv import load_dotenv

load_dotenv()


def _get_mysql_module():
    try:
        import mysql.connector
        return mysql.connector
    except Exception:
        return None


def _env(keys: tuple[str, ...], default=None):
    """Return the first env var found in `keys` (helper for legacy names)."""
    for key in keys:
        value = os.environ.get(key)
        if value not in (None, ""):
            return value
    return default


def get_db_config(dbname=None):
    """Return a dict with connection parameters read from environment (.env).

    Supports both the new (`DB_USER`, `DB_NAME`) and legacy (`DB_USERNAME`,
    `DB_DATABASE`) variable names so existing deployments continue to work.
    """
    return {
        'host': _env(('DB_HOST',), '127.0.0.1'),
        'port': int(_env(('DB_PORT',), 3306)),
        'user': _env(('DB_USER', 'DB_USERNAME')),
        'password': _env(('DB_PASSWORD', 'DB_PASS')),
        'database': dbname or _env(('DB_NAME', 'DB_DATABASE')),
    }


def get_conn(dbname=None):
    """Return a new mysql.connector connection. Caller is responsible for closing it.

    Raises RuntimeError if mysql.connector is not installed or connection fails.
    """
    mysql = _get_mysql_module()
    if mysql is None:
        raise RuntimeError('mysql.connector is not installed. Please install mysql-connector-python')
    cfg = get_db_config(dbname)
    try:
        return mysql.connect(**cfg)
    except Exception:
        raise


@contextmanager
def cursor(dbname=None):
    """Context manager yielding (conn, cur). Ensures close in finally."""
    conn = None
    cur = None
    try:
        conn = get_conn(dbname)
        cur = conn.cursor()
        yield conn, cur
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def test_connection(dbname=None):
    """Try to connect and return a small report dict. Raises on fatal errors.

    Returns: {'ok': True, 'database': str, 'version': str}
    """
    mysql = _get_mysql_module()
    if mysql is None:
        return {'ok': False, 'error': 'mysql.connector not installed'}
    try:
        with cursor(dbname) as (conn, cur):
            cur.execute('SELECT DATABASE(), VERSION()')
            row = cur.fetchone()
            dbname_res = row[0] if row and row[0] is not None else conn.database
            version = row[1] if row and len(row) > 1 else None
            return {'ok': True, 'database': dbname_res, 'version': version}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'trace': traceback.format_exc()}


def get_awb_in_transit():
    """Restituisce la lista di AWB con final_position = 0 dalla tabella spedizioni."""
    awb_list = []
    try:
        with cursor() as (conn, cur):
            cur.execute("SELECT awb FROM spedizioni WHERE final_position = 0 AND awb IS NOT NULL AND awb != ''")
            rows = cur.fetchall()
            awb_list = [row[0] for row in rows]
    except Exception as e:
        print(f"Errore lettura AWB in transito: {e}")
    return awb_list


def update_last_position(awb, status):
    """Aggiorna il campo last_position per una spedizione dato l'AWB."""
    try:
        with cursor() as (conn, cur):
            cur.execute("UPDATE spedizioni SET last_position = %s WHERE awb = %s", (status, awb))
            conn.commit()
    except Exception as e:
        print(f"Errore aggiornamento last_position per AWB {awb}: {e}")


if __name__ == '__main__':
    print('Testing DB connection using .env credentials...')
    r = test_connection()
    if r.get('ok'):
        print('Connection OK')
        print('Database:', r.get('database'))
        print('MySQL version:', r.get('version'))
    else:
        print('Connection FAILED')
        print(r)
