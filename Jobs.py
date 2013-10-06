#!/usr/bin/python
import HandBrakeCLI
import Globals
import Screenshots

import glob
import multiprocessing
import time
import logging
import shutil
import os
import fcntl
import select
import re
import sys
from time import sleep

class Job:
    def __init__(self, handbrakeoptions=None, jobID=None):
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
        elif jobID:
            self.load(jobID)

    def load(self, jobID):
        self.id = jobID
        r = Globals.db.query("SELECT arguments FROM job where ID = (?)",(self.id,),True)
        if r['arguments']:
            self.hb.Options.setDefaults()
            self.hb.Options.fromJSON(r['arguments'])

    def is_active(self):
        Globals.db.query("SELECT status FROM job WHERE ID = (?)",(self.id,),True)
        pass

    def is_canceled(self):
        ret = Globals.db.query("SELECT status FROM job WHERE ID = (?)",(self.id,),True)
        if ret['status'] == 'Canceled':
            return True
        return False

    def run(self):
        if not Globals.db.query("SELECT status FROM job where ID = (?)",(self.id,),True):
            Globals.Log.debug("Could not find ID %s in database, will not run" % self.id)
            return
        if self.is_canceled():
            Globals.Log.debug("Job %i is marked as canceld, will not run" % self.id)
            return
        timeStart = time.time()
        savedPath = os.getcwd()
        outPath = "static/jobs/" + str(self.id) + "/"
        if not os.path.exists(outPath):
            os.mkdir(outPath)
        os.chdir(outPath)        
        try:
            self.jobLog = logging.getLogger("WebRake.Job" + str(self.id))
            self.setStatus('Initializing')
            self.prep()
            self.setStatus('Encoding')
            self.jobLog.debug("Starting job " + str(self.id) + " with command " + ' '.join(self.hb.Options.toArgArray()))
            self.encode()
            self.setStatus('Finalizing')
            self.finish()
            self.setStatus('Finished')
            seconds = (time.time() - timeStart)
            hours = seconds // (60*60)
            seconds %= (60*60)
            minutes = seconds // 60
            seconds %= 60
            self.setStatus('Finished: %02i:%02i:%02i' % (hours, minutes, seconds))
            self.jobLog.debug("Encoded file in %f seconds" % (seconds))
        except Exception as e:
            print sys.exc_info()[0]
            Globals.Log.debug("Job %d failed with message \"%s\"" % (self.id, e))
            self.setStatus('Failed:%s' % e)
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
        with open('scan.log', 'w') as f:
            f.write(stderr)
        r = re.compile('autocrop: (\d+)/(\d+)/(\d+)/(\d+)')
        m = r.search(stderr)
        if m is not None:
            autoCrop = [m.group(1), m.group(2), m.group(3), m.group(4)]
            self.jobLog.debug("Autocrop scan match: " + str(autoCrop))
            if not self.hb.Options.Crop:
                self.hb.Options.Crop = autoCrop
                conn = Globals.db.conn()
                cur = conn.cursor()
                cur.execute("UPDATE job SET arguments = (?) WHERE id = (?)", (self.hb.Options.toJSON(),self.id))
                conn.commit()
                conn.close()

    def encode(self):
        sp = self.hb.encode()
        #sp.start()
        # Reading from a command's output in real time is quite an exercise
        fcntl.fcntl(sp.stdout.fileno(), fcntl.F_SETFL,  fcntl.fcntl(sp.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
        ETA = ""
        output = ""
        while sp.poll() == None:
            out = select.select([sp.stdout.fileno()], [], [])[0]
            if not out:
                continue
            else:
                chunk = sp.stdout.read()
                output = output + chunk
                if chunk.find("ETA") > 0:
                    ETAnow = str(chunk[(chunk.find("ETA")+4):(chunk.find("ETA")+13)])
                    if not ETAnow == ETA:
                        ETA = ETAnow
                        self.setStatus('Encoding: ETA %s' % ETA)
        with open('encode.log', 'w'):
            f.write(output)


    def finish(self):
        outDir = "/home/kannibalox/MyEnv/WebRake/static/jobs/" + str(self.id) + "/"
        S = Screenshots.Screenshots(self.id, outDir)
        S.takeAllPreviewScreenshots()

class JobManager:
    def __init__(self):
        Globals.Log.debug("Initializing job manager")
        self.Log = logging.getLogger("WebRake.JobManager")
        self.runningJob = multiprocessing.Queue()
        self.actionQueue = multiprocessing.Queue()
        self.jobQueue = multiprocessing.Queue()
        self.die = False
        self.worker = multiprocessing.Process(target=self.workQueue)
        self.worker.start()

    def removeJob(self, jobID):
        pass

    def addJob(self, HandbrakeOptions):
        job = Job(HandbrakeOptions)
        self.jobQueue.put(job.id)

    def startJob(self, jobID):
        job = Job(jobID=jobID)
        p = multiprocessing.Process(target=job.run)
        p.start()
        self.runningJob = p

    def workQueue(self):
        while True:
            job = Job(jobID=self.jobQueue.get())
            job.run()

    def purgeJob(self, jobID):
        self.Log.info("Purging job %i" % jobID)
        job = Job(jobID=jobID)
        static_dir = "static/jobs/" + str(jobID)
        images = glob.glob(static_dir + '/*.png');
        videos = glob.glob(static_dir + '/*.mkv');
        if len(images) > 0:
            del(images[0]) # Save one image
        for i in images:
            os.remove(i)
        for v in videos:
            os.remove(v)
        return len(images) + len(videos)


    def killRunningJob(self):
        if self.runningJob:
            self.runningJob.terminate()
            return "Terminated"
        return "Not running %s" % self.runningJob
        
    def action(self, action, args=None):
        self.actionQueue.put((action,args))

def init():
    global Manager
    Manager = JobManager()
