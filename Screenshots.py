import subprocess
import os
import os.path
import shutil
import json
import Globals

class Screenshots:
    def __init__(self, actionID, outDir, numScreenshots=5):
        self.imagePaths = []
        self.numScreenshots = numScreenshots
        self.ID = actionID
        self.outDir = outDir
        self.FilePath = os.path.join(outDir, json.loads(Globals.db.query("SELECT arguments FROM job where ID = ?", (self.ID,), one=True)['arguments'])['Output'])

    def takeScreenshot(self, time="10"):
        args = [ "mplayer", "-ss", str(time), "-vo", "png:z=9", "-frames", "1", "-vf", "scale=0:0", "-nosound", "-nosub", "-nolirc", self.FilePath ]
        print " ".join(args)
        proc = subprocess.Popen( args, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
        stdout, stderr = proc.communicate()
        print stdout
        errorCode = proc.wait()
        if errorCode != 0:
            Log.debug("Screenshot process returned a non-zero exit code")
        return errorCode

    def takeAllPreviewScreenshots(self):
        # Mplayer doesn't take the last screenshot for some reason,
        ##so that's the reason for the weird math
        prevLength = 30
        interval = (prevLength)/(self.numScreenshots+2)
        for i in range(interval, prevLength-(interval*2), interval):
            Globals.Log.debug("Taking screenshot at interval %i" % i)
            if os.path.exists(os.path.join(self.outDir, 'Preview%d.png' % i)):
                continue
            self.takeScreenshot(i)
            try:
                os.rename('00000001.png', 'Preview%d.png' % i)
            except OSError:
                Globals.Log.info("Could not generate screenshot at interval %d" % i)

if __name__ == "__main__":
    s = Screenshots(9)
    s.takeAllPreviewScreenshots()
