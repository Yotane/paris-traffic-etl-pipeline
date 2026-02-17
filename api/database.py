import mysql.connector
from mysql.connector.connection import MySQLConnection
import sys
import os
import logging

logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

def get_connection() -> MySQLConnection:
    """
    Create and return a MySQL database connection.
    
    Returns:
        MySQLConnection object
        
    Raises:
        mysql.connector.Error if connection fails
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Database connection failed: {err}")
        raise

def execute_query(query: str, params: tuple = None) -> list:
    """
    Execute a SELECT query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters (for parameterized queries)
        
    Returns:
        List of row dictionaries
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
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        Number of affected rows
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