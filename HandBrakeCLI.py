import subprocess
import fcntl
import select
import os
import time
import simplejson, json
import re

class HandBrakeOptions:
    MAIN_FEATURE = "--main-feature"

    def __init__(self):
        self.Output = ""
        self.Input = ""
        self.x264opts = ""
        self.Crop = []
        self.FrameRate = ""
        self.Title = ""
        self.Quality = ""
        self.VideoBitRate = ""
        self.AudioUse = []
        self.AudioEncoder = []
        self.AudioBitRate = []
        self.SubtitleUse = []
        self.IncludeChapters = ""
        self.Duration = []
        self.AddtlOpts = []
        self.isPreview = None
        self.Detelecine = None
        self.Deinterlace = None
        self.x264Preset = ""
        self.x264Tune = ""
        self.Anamorphic = ""

    # Set up sane x264 encoding defaults
    def setDefaults(self):
        self.Output = "out.mkv"
        self.x264Preset = "placebo"
        self.x264Tune = "film"
        self.FrameRate = "23.976"
        self.Title = HandBrakeOptions.MAIN_FEATURE
        self.Quality = '17'
        self.AudioEncoder = 'copy'
        self.IncludeChapters = True
        self.isPreview = True
        self.x264opts = "aq-mode=2:ref=12:merange=32"
        self.Anamorphic = "strict"

    def toJSON(self):
        return json.dumps(self.__dict__)

    def fromJSON(self, jsonStr):
        d = json.loads(jsonStr)
        for attr in d.keys():
            setattr(self, attr, d[attr])
    
    # Fairly straight-forward array building
    def toArgArray(self):
        retArray = []
        if not self.Input:
            Log.severe("Must have input file!")
        retArray += ['-i', self.Input]
        if self.Output:
            retArray += ['-o', self.Output]
        if self.Crop:
            retArray += ['--crop', ':'.join(self.Crop)]
        if self.Detelecine:
            retArray += ['--detelecine']
        if self.Deinterlace:
            retArray += ['--deinterlace']
        if self.IncludeChapters:
            retArray += ['-m']
        if self.AudioUse:
            retArray += ['-a', ','.join(self.AudioUse)]
        if self.Title:
            if self.Title == HandBrakeOptions.MAIN_FEATURE:
                retArray += [HandBrakeOptions.MAIN_FEATURE]
            else:
                retArray += ['-t', self.Title]
        if self.SubtitleUse:
            retArray += ['-s', self.SubtitleUse]
        if self.Quality:
            retArray += ['-q', self.Quality]
        if self.isPreview and not self.Duration:
            retArray += ["--start-at", "duration:400", "--stop-at", "duration:30"]
        elif self.Duration:
            retArray += ["--start-at", "duration:%s" % self.Duration[0], "--stop-at", "duration:%s" % self.Duration[1]]
        if self.AudioEncoder:
            retArray += ['-E', self.AudioEncoder]
        if self.FrameRate:
            retArray += ['-r', self.FrameRate]
        if self.Anamorphic:
            retArray += ['--%s-anamorphic' % self.Anamorphic.lower()]
        if self.x264Preset:
            retArray += ['--x264-preset', self.x264Preset]
        if self.x264Tune:
            retArray += ['--x264-tune', self.x264Tune]
        if self.x264opts:
            retArray += ['-x', self.x264opts]
        retArray += ['-e', 'x264']
        if self.AddtlOpts:
            retArray += self.AddtlOpts.split(' ') # Can't handle quotes for right now
        return retArray

class HandBrakeCLI:
    def __init__(self):
        self.HandBrakePath = "HandBrakeCLI"
        self.Width = 0
        self.Height = 0
        self.AudioTracks = []
        self.SubTracks = []
        self.Test = 5
        self.Options = HandBrakeOptions()
        self.ETA = ""
        self.autoCrop = []
        
    def scan(self):
        scanStrings = subprocess.Popen([self.HandBrakePath, "--main-feature", "-i", self.Options.Input, "-t", "0", "-v", "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        return scanStrings

    def encode(self):
        sp = subprocess.Popen([self.HandBrakePath] + self.Options.toArgArray(), stdout= subprocess.PIPE, stderr= subprocess.PIPE)
        return sp
        print("Opening HandBrake thread")
        # HandBrake doesn't output newlines until finished, so real-time output reading is quite an excercise
        fcntl.fcntl(sp.stdout.fileno(), fcntl.F_SETFL,  fcntl.fcntl(sp.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
        while sp.poll() == None:
            out = select.select([sp.stdout.fileno()], [], [])[0]
            if not out:
                continue
            chunk = sp.stdout.read()
            if chunk.find("ETA") > 0:
                ETAnow = str(chunk[(chunk.find("ETA")+4):(chunk.find("ETA")+13)])
                if not ETAnow == self.ETA:
                    print("Found ETA. It is " + ETAnow)
                    self.ETA = ETAnow
        print("Handbrake thread completed successfully")
        return "Done"

    # Parses a HandBrake scan for information. Rather hackish at the moment.
    def parseScan(self, scanLines):
        lineIter = iter(scanLines.splitlines())
        for line in lineIter:
            if line.find("Found main feature title") >= 0:
                print "Main feature was found, starting parse"
                next(lineIter) # Skip title length
                next(lineIter) # Skip title identifier line
                while True:
                    try: 
                        mainLine = next(lineIter)
                    except StopIteration:
                        print "End of scan, exiting..."
                        return
                    print mainLine
                    if mainLine[0] == '+':
                        print "Next title found"
                        break
                    propName, separator, propVal = mainLine.strip(' +').partition( ": " )
                    if propName == 'audio tracks:':
                        print "Start of audio tracks"
                        while True:
                            nextStr = next(lineIter)
                            if nextStr[0:6] == '    + ':
                                print "Audio track found"
                                self.AudioTracks.append(nextStr.partition(', ')[2])
                            else:
                                print self.AudioTracks
                                print "End of audio tracks"
                                propName, separator, propVal = nextStr.strip(' +').partition( ": " )
                                break
                    if propName == 'subtitle tracks:':
                        print "Start of subtitle tracks"
                        while True:
                            try:
                                nextStr = next(lineIter)
                            except StopIteration:
                                return
                            if nextStr[0:6] == '    + ':
                                print "Subtitle track found"
                                self.SubTracks.append(nextStr.partition(', ')[2])
                            else:
                                print self.SubTracks
                                print "Done finding subs"
                                propName, separator, propVal = nextStr.strip(' +').partition( ": " )
                                break
                    propName, separator, propVal = mainLine.strip(' +').partition( ": " )
                    if propName == "autocrop":
                        self.Crop = propVal.split('/')
                        print self.Crop
                    if propName == "duration":
                        h, m, s = propVal.split(':')
                        self.Duration = (int(h) * 60 * 60) + (int(m) * 60) + int(s)
                        print self.Duration
                    if propName == "size":
                        subProps = mainLine.strip(' +').split(',')
                        self.Width = subProps[0].partition( ": " )[2].split('x')[0]
                        self.Height = subProps[0].partition( ": " )[2].split('x')[1]
                        print self.Width,'x',self.Height
def main():
    hb = HandBrakeCLI()
    hb.Options.setDefaults()
    print hb.Options.toJSON()
    hb.Options.fromJSON(hb.Options.toJSON())

if __name__ == '__main__': 
    main()
