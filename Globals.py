import Config
import multiprocessing
import logging
import sqlite3
import os

Log = None
db = None

class Database:
    def __init__(self, dbFile):
        self.dbFile = os.path.abspath(dbFile)

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

    def query(self, query, args=(), one=False):
        conn = sqlite3.connect(self.dbFile)
        cur = conn.execute(query, args)
        rv = [dict((cur.description[idx][0], value) for idx, value in enumerate(row)) for row in cur.fetchall()]
        return (rv[0] if rv else None) if one else rv

    def conn(self):
        return sqlite3.connect(self.dbFile)

def init():
    global Config
    global Log
    global db

    Config.loadSettings()
    
    Log = logging.getLogger("WebRake")
    Log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    format = logging.Formatter ( "[%(asctime)s] %(levelname)-8s %(name)s %(message)s", "%Y-%m-%d %H:%M:%S" )
    ch.setFormatter( format )
    ch.setLevel(logging.DEBUG)
    logFile = 'messages.log'
    fh = logging.FileHandler(logFile)
    fh.setFormatter( format )
    ch.setLevel(logging.DEBUG)
    Log.addHandler(ch)
    Log.debug("Stdout log handler initialized")
    Log.addHandler(fh)
    Log.debug("Log file %s initialized" % logFile)

    db = Database(Config.Database)
    db.init_db()
