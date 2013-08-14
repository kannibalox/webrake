import Config
import multiprocessing
import logging
import sqlite3
import os

Log = None
db = None

class Database:
    def __init__(self, dbFile):
        self.dbFile = dbFile

    def init_db(self):
        try:
            conn = sqlite3.connect(self.dbFile)
            conn.execute("SELECT * FROM job")
        except sqlite3.OperationalError:
            Log.debug("Initalizing database file at " + self.dbFile)
            qry = open('schema.sql', 'r').read()
            conn = sqlite3.connect(self.dbFile)
            conn.executescript(qry)
            conn.commit()
            conn.close()

    def query_db(self, query, args=(), one=False):
        conn = sqlite3.connect(self.dbFile)
        cur = conn.execute(query, args)
        rv = [dict((cur.description[idx][0], value) for idx, value in enumerate(row)) for row in cur.fetchall()]
        return (rv[0] if rv else None) if one else rv

    def conn(self):
        return sqlite3.connect(self.dbFile)

# Wrapper class for the python logger
class Logger:
    def __init__(self):
        self.Log = logging.getLogger("WebRake")
        self.Log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        format = logging.Formatter ( "[%(asctime)s] %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S" )
        ch.setFormatter( format )
        ch.setLevel(logging.DEBUG)
        self.Log.addHandler(ch)
        self.Log.debug("Stdout log handler initialized")

    def debug(self, message):
        self.Log.debug(message)

    def info(self, message):
        self.Log.info(message)
        
    def error(self, message):
        self.Log.error(message)

    def warning(self, message):
        self.Log.warning(message)
        

def init():
    global Config
    global Log
    global db

    Config.loadSettings()
    
    Log = Logger()

    db = Database(Config.Database)
    db.init_db()
