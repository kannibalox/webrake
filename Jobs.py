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

    def load(self, jobID):
        self.id = jobID
        r = Globals.db.query("SELECT arguments FROM job where ID = (?)",(self.id,),True)
        if r['arguments']:
            self.hb.Options.setDefaults()
            self.hb.Options.fromJSON(r['arguments'])

    def run(self):
        if not Globals.db.query("SELECT status FROM job where ID = (?)",(self.id,),True):
            Globals.Log.debug("Could not find ID %s in database, will not run" % self.id)
        timeStart = time.time()
        savedPath = os.getcwd()
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
            os.chdir(savedPath)

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
        self.jobQueue = []
        self.die = False

    def removeJob(self, jobID):
        pass

    def startJob(self, jobID):
        job = Job()
        job.load(jobID)
        job.run()
        self.runningJob = None
        
        pass

    def purgeJob(self, jID):
        pass

    def killRunningJob(self):
        if self.runningJob:
            self.runningJob.terminate()
            return "Terminated"
        return "Not running %s" % self.runningJob
        
    def action(self, action, args=None):
        self.actionQueue.put((action,args))

    def run(self):
        self.workQueue()

    def kill(self):
        self.mProcess.terminate()

    def workQueue(self):
        Globals.Log.info("Started action queue worker")
        while not self.die:
            action = self.actionQueue.get()
            if action[0] == "runJobs":
                if self.runningJob is None:
                    jobID = self.jobQueue.pop(0)
                    job = Job()
                    job.load(jobID)
                    self.runningJob = multiprocessing.Process(target=self.startJob,args=(jobID,))
                    self.runningJob.start()
                else:
                    Globals.Log.debug("A job (%s) is already running: not starting a new thread" % self.runningJob)
            elif action[0] == "add":
                newJob = Job(action[1])
                self.jobQueue.append(newJob.id)
                self.actionQueue.put(("runJobs",))
            elif action[0] == "interrupt":
                print "Killing %s" % self.runningJob
                if self.runningJob:
                    self.runningJob.terminate()
            elif action[0] == "stop":
                print "Removing job %i" % action[1]
                self.removeJob(action[1])
            elif action[0] == "die":
                self.die = True
            else:
                Globals.Log.debug("Action %s not recognized" % action[0])
        Globals.Log.info("Exiting action queue worker")

def startManager():
    global Manager
    Manager = JobManager()
    Manager.start()

def stopManager():
    Manager.terminate()
