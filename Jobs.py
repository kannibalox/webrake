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
import re
import sys

class Job:
    def __init__(self, handbrakeoptions=None):
        self.hb = HandBrakeCLI.HandBrakeCLI()
        if handbrakeoptions:
            self.hb.Options = handbrakeoptions
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
        self.savedPath = os.getcwd()
        outPath = "static/jobs/" + str(self.id) + "/"
        if not os.path.exists(outPath):
            os.mkdir(outPath)
        os.chdir(outPath)        
        try:
            self.jobLog = logging.getLogger("WebRake." + str(self.id))
            self.setStatus('Initializing')
            self.prep()
            self.setStatus('Encoding')
            self.jobLog.debug("Starting job " + str(self.id) + " with command " + ' '.join(self.hb.Options.toArgArray()))
            self.encode()
            self.setStatus('Finalizing')
            self.finish()
            self.setStatus('Finished')
            timeDelta = time.time() - timeStart
            timeDeltaStr = "%ih%im%is" % (round(timeDelta/(60*60)), round((timeDelta-60)/60), timeDelta%60)
            self.setStatus('Finished: %s' % timeDeltaStr)
            self.jobLog.debug("Encoded file in %f seconds" % (timeDelta))
        except Exception as e:
            print sys.exc_info()[0]
            Globals.Log.debug("Job %d failed with message \"%s\"" % (self.id, e))
            self.setStatus('Failed')
        finally:
            self.jobLog = None
            os.chdir(self.savedPath)            

    def setStatus(self, status):
        conn = Globals.db.conn()
        cur = conn.cursor()
        cur.execute("UPDATE job SET status = (?) WHERE id = (?)", (status, self.id))
        conn.commit()
        conn.close()

    def prep(self):
        stderr = self.hb.scan()[1]
        r = re.compile('autocrop: (\d+)/(\d+)/(\d+)/(\d+)')
        m = r.search(stderr)
        autoCrop = [m.group(1), m.group(2), m.group(3), m.group(4)]
        Globals.Log.debug("Autocrop scan match: " + str(autoCrop))
        if not self.hb.Options.Crop:
            self.hb.Options.Crop = autoCrop
        conn = Globals.db.conn()
        cur = conn.cursor()
        cur.execute("UPDATE job SET arguments = (?) WHERE id = (?)", (self.hb.Options.toJSON(),self.id))
        conn.commit()
        conn.close()

    def encode(self):
        sp = self.hb.encode()
        # Reading from a command's output in real time is quite an exercise
        fcntl.fcntl(sp.stdout.fileno(), fcntl.F_SETFL,  fcntl.fcntl(sp.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
        ETA = ""
        while sp.poll() == None:
            out = select.select([sp.stdout.fileno()], [], [])[0]
            if not out:
                continue
            else:
                chunk = sp.stdout.read()
                if chunk.find("ETA") > 0:
                    ETAnow = str(chunk[(chunk.find("ETA")+4):(chunk.find("ETA")+13)])
                    if not ETAnow == ETA:
                        ETA = ETAnow
                        self.setStatus('Encoding: %s' % ETA)

    def finish(self):
        outDir = "/home/kannibalox/MyEnv/WebRake/static/jobs/" + str(self.id) + "/"
        S = Screenshots.Screenshots(self.id, outDir)
        S.takeAllPreviewScreenshots()

class JobManager(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.runningJob = None
        self.actionQueue = multiprocessing.Queue()
        self.jobQueue = multiprocessing.Queue()
        self.die = False

    def addJob(self, handbrakeoptions):
        newJob = Job(handbrakeoptions)
        self.jobQueue.put(newJob)
        self.actionQueue.put("runJobs")
    
    def removeJob(self, jID):
        pass

    def startJob(self, jID):
        if self.runningJob:
            Globals.Log.warning("Tried to start two jobs at the same time!")
            return
        pass

    def purgeJob(self, jID):
        pass

    def killRunningJob(self):
        if self.runningJob:
            self.runningJob.terminate()
            return "Terminated"
        return "Not running %s" % self.runningJob
        

    def run(self):
        self.workQueue()

    def kill(self):
        self.mProcess.terminate()

    def workQueue(self):
        Globals.Log.info("Started action queue worker")
        while not self.die:
            action = self.actionQueue.get()
            if action == "runJobs":
                job = self.jobQueue.get()
                self.runningJob = multiprocessing.Process(target=job.run)
                self.runningJob.start()
            elif action == "die":
                self.die = True
            elif action == "interrupt":
                print "Killing %s" % self.runningJob
                if self.runningJob:
                    self.runningJob.terminate()
            else:
                Globals.Log.debug("Action %s not recognized" % action)
        Globals.Log.info("Exiting action queue worker")

def startManager():
    global Manager
    Manager = JobManager()
    Manager.start()

def stopManager():
    Manager.terminate()
