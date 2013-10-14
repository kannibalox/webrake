import subprocess
import simplejson, json

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

def main():
    hb = HandBrakeCLI()
    hb.Options.setDefaults()
    print hb.Options.toJSON()
    hb.Options.fromJSON(hb.Options.toJSON())

if __name__ == '__main__': 
    main()
