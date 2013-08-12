#!/usr/bin/python
import HandBrakeCLI
import multiprocessing
from time import sleep
import Globals
import shutil
import os
import Screenshots

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
        self.setStatus('Running')
        Globals.Log.debug("Starting job " + str(self.id))
        self.hb.encode()
        self.setStatus('Finalizing')
        self.finish()
        self.setStatus('Finished')
        pass

    def setStatus(self, status):
        conn = Globals.db.conn()
        conn.execute("UPDATE job SET status = (?) WHERE id = (?)", (status, self.id))
        conn.commit()
        conn.close()

    def finish(self):
        outDir = "/home/kannibalox/MyEnv/Encoder/static/jobs/" + str(self.id) + "/"
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

    def startJob(Self, jID):
        pass

    def workQueue(self):
        Globals.Log.info("Started queue worker")
        while True:
            runningJob = self.jobQueue.get()
            self.runningJob = runningJob
            runningJob.run()
