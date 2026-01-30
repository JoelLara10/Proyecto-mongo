import pymysql

DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASS = ''
DB_NAME = 'ineo_db'

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
