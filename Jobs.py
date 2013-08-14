#!/usr/bin/python
import HandBrakeCLI
import Globals
import Screenshots

import multiprocessing
import time
import logging
import shutil
import os
import fcntl
import select

class Job:
    def __init__(self, handbrake=None):
        self.hb = handbrake
        self.id = None
        conn = Globals.db.conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO job(status, arguments) VALUES('Queued', (?))", (self.hb.Options.toJSON(),))
        self.id = cur.lastrowid
        conn.commit()
        conn.close()
        Globals.Log.debug("Added job " + str(self.id))

    def run(self):
        timeStart = time.time()
        self.setStatus('Encoding')
        Globals.Log.debug("Starting job " + str(self.id))
        self.encode()
        self.setStatus('Finalizing')
        self.finish()
        self.setStatus('Finished')
        timeStop = time.time()
        timeDelta = timeStop - timeStart
        timeDeltaStr = "%ih%im%is" % (round(timeDelta/(60*60)), round((timeDelta-60)/60), timeDelta%60)
        self.setStatus('Finished: %s' % timeDeltaStr)
        Globals.Log.debug("Encoded file in %f seconds" % (timeStop - timeStart))

    def setStatus(self, status):
        conn = Globals.db.conn()
        conn.execute("UPDATE job SET status = (?) WHERE id = (?)", (status, self.id))
        conn.commit()
        conn.close()

    def encode(self):
        sp = self.hb.encode()
        fcntl.fcntl(sp.stdout.fileno(), fcntl.F_SETFL,  fcntl.fcntl(sp.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
        ETA = ""
        while sp.poll() == None:
            out = select.select([sp.stdout.fileno()], [], [])[0]
            if not out:
                continue
            chunk = sp.stdout.read()
            if chunk.find("ETA") > 0:
                ETAnow = str(chunk[(chunk.find("ETA")+4):(chunk.find("ETA")+13)])
                if not ETAnow == ETA:
                    ETA = ETAnow
                    self.setStatus('Encoding: %s' % ETA)


    def finish(self):
        outDir = "/home/kannibalox/MyEnv/WebRake/static/jobs/" + str(self.id) + "/"
        if not os.path.exists(outDir):
            os.mkdir(outDir)
        S = Screenshots.Screenshots(self.id, outDir)
        S.takeAllPreviewScreenshots()
        shutil.move(self.hb.Options.Output, outDir)

class JobManager:
    def __init__(self):
        self.runningJob = None
        self.jobQueue = multiprocessing.Queue()

    def addJob(self, handbrake):
        newJob = Job(handbrake)
        self.jobQueue.put(newJob)
    
    def removeJob(self, jID):
        pass

    def startJob(self, jID):
        pass

    def purgeJob(self, jID):
        pass

    def workQueue(self):
        Globals.Log.info("Started queue worker")
        while True:
            runningJob = self.jobQueue.get()
            self.runningJob = runningJob
            runningJob.run()

def startManager():
    global Manager
    Manager = JobManager()
    multiprocessing.Process(target=Manager.workQueue).start()

