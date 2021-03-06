#!/usr/bin/python
import HandBrakeCLI
import Globals
import Screenshots
import Config

import json
import glob
import multiprocessing
import time
import logging
import shutil
import os
import os.path
import fcntl
import select
import re
import sys
import traceback
from time import sleep

class Job:
    def __init__(self, handbrakeoptions=None, jobID=None):
        self.hb = HandBrakeCLI.HandBrakeCLI()
        if handbrakeoptions:
            self.hb.Options = handbrakeoptions
            self.id = Globals.db.insert("INSERT INTO job(status, arguments) VALUES('Queued', (?))", (self.hb.Options.toJSON(),))
            Globals.Log.debug("Added job " + str(self.id))
        elif jobID:
            self.load(jobID)
        self.workDirectory = os.path.join(Config.JobsDirectory, str(self.id), '')
        if not os.path.exists(self.workDirectory):
            os.mkdir(self.workDirectory)

    def load(self, jobID):
        self.id = jobID
        r = Globals.db.query("SELECT arguments FROM job where ID = (?)",(self.id,),True)
        if r['arguments']:
            self.hb.Options.setDefaults()
            self.hb.Options.fromJSON(r['arguments'])

    def is_canceled(self):
        ret = Globals.db.query("SELECT status FROM job WHERE ID = (?)",(self.id,),True)
        if ret['status'] == 'Canceled' or ret['status'] == 'Deleted':
            return True
        return False

    def run(self):
        if not Globals.db.query("SELECT status FROM job where ID = (?)",(self.id,),True):
            Globals.Log.debug("Could not find ID %s in database, will not run" % self.id)
            return
        if self.is_canceled():
            Globals.Log.debug("Job %i is marked as canceled, will not run" % self.id)
            return
        timeStart = time.time()
        savedPath = os.getcwd()
        os.chdir(self.workDirectory) 
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
            print(traceback.format_exc(sys.exc_info()))
            Globals.Log.debug("Job %d failed with message \"%s\"" % (self.id, e))
            self.setStatus('Failed:%s' % e)
        finally:
            self.jobLog = None
            os.chdir(savedPath)

    def setStatus(self, status):
        Globals.db.update("UPDATE job SET status = (?) WHERE id = (?)", (status, self.id))

    def prep(self):
        stderr = self.hb.scan()[1]
        with open('scan.log', 'wb') as f:
            f.write(stderr)
        r = re.compile(b'autocrop: (\d+)/(\d+)/(\d+)/(\d+)')
        m = r.search(stderr)
        if m is not None:
            autoCrop = [m.group(1).decode(), m.group(2).decode(), m.group(3).decode(), m.group(4).decode()]
            self.jobLog.debug("Autocrop scan match: " + str(autoCrop))
            if not self.hb.Options.Crop:
                self.hb.Options.Crop = autoCrop
                conn = Globals.db.update("UPDATE job SET arguments = (?) WHERE id = (?)", (self.hb.Options.toJSON(),self.id))

    def encode(self):
        sp = self.hb.encode()
        # Reading from a command's output in real time is quite an exercise
        fcntl.fcntl(sp.stdout.fileno(), fcntl.F_SETFL,  fcntl.fcntl(sp.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
        ETA = ""
        output = ""
        while sp.poll() == None:
            outstd = select.select([sp.stdout.fileno()], [], [])[0]
            if not outstd:
                continue
            else:
                chunk = sp.stdout.read().decode()
                if chunk.find("ETA") > 0:
                    ETAnow = str(chunk[(chunk.find("ETA")+4):(chunk.find("ETA")+13)])
                    if not ETAnow == ETA:
                        ETA = ETAnow
                        self.setStatus('Encoding: ETA %s' % ETA)
        with open('encode.log', 'wb') as f:
            for line in sp.stderr:
                f.write(line)

    def finish(self):
        S = Screenshots.MpvScreenshots(self.id, self.workDirectory)
        S.takeAllPreviewScreenshots()

class JobManager:
    def __init__(self):
        Globals.Log.debug("Initializing job manager")
        self.Log = logging.getLogger("WebRake.JobManager")
        self.runningJob = None
        self.jobQueue = multiprocessing.Queue()
        self.worker = multiprocessing.Process(target=self.workQueue)
        self.worker.start()

    def __catchInterruptedJobs(self):
        cur = Globals.db.query("SELECT ID FROM job WHERE status NOT LIKE 'Finished%' AND status <> 'Queued' AND Status NOT LIKE 'Failed%'")
        for row in cur:
            j = Job(jobID=row['id'])
            j.setStatus("Interrupted")

    def exportJob(self, jobID):
        path = os.path.join(self.workDirectory, json.loads(Globals.db.query("SELECT arguments FROM job WHERE id = (?)", (jobID,), True)['arguments'])['Output'])
        shutil.move(path, Config.ExportDirectory)

    def removeJob(self, jobID):
        job = Job(jobID=jobID)
        job.setStatus("Deleted")
        try:
            shutil.rmtree(job.workDirectory)
        except OSError:
            pass

    def finalizeJob(self, jobID):
        jInput = json.loads(Globals.db.query("SELECT arguments FROM job WHERE id = (?)", (jobID,), True)['arguments'])['Input']
        print(jInput)
        cur = Globals.db.query("SELECT ID, arguments FROM job WHERE id < (?)", (jobID,))
        for row in cur:
            if json.loads(Globals.db.query("SELECT arguments FROM job WHERE id = (?)", (row['id'],), True)['arguments'])['Input'] == jInput:
                self.removeJob(row['id'])

    def addJob(self, HandbrakeOptions):
        job = Job(HandbrakeOptions)
        self.jobQueue.put(job.id)

    def workQueue(self):
        while True:
            job = Job(jobID=self.jobQueue.get())
            job.run()

    def purgeJob(self, jobID):
        self.Log.info("Purging job %i" % jobID)
        job = Job(jobID=jobID)
        images = glob.glob(os.path.join(job.workDirectory, '/*.png'));
        videos = glob.glob(os.path.join(job.workDirectory, '/*.mkv'));
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
        
def init():
    global Manager
    Manager = JobManager()
