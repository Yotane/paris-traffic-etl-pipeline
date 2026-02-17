import mysql.connector
from mysql.connector.connection import MySQLConnection
import sys
import os
import logging

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_CONFIG

def get_connection() -> MySQLConnection:
    """
    Create and return a MySQL database connection.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Database connection failed: {err}")
        raise

def execute_query(query: str, params: tuple = None) -> list:
    """
    Execute a SELECT query and return results as list of dictionaries.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        return results
    finally:
        cursor.close()
        conn.close()

def execute_write(query: str, params: tuple = None) -> int:
    """
    Execute an INSERT, UPDATE, or DELETE query.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.rowcount
    except mysql.connector.Error as err:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()