from Config import conf
import multiprocessing
import Jobs
import logging
import sqlite3
import os

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


def initializeLogger():
    Log = logging.getLogger("WebRake")
    Log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    format = logging.Formatter ( "[%(asctime)s] %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S" )
    ch.setFormatter( format )
    ch.setLevel(logging.DEBUG)
    Log.addHandler(ch)
    Log.debug("Stdout log handler initialized")
    return Log



Log = initializeLogger()

db = Database(conf.get('Main','DB'))
db.init_db()

Manager = Jobs.JobManager()
multiprocessing.Process(target=Manager.workQueue).start()
