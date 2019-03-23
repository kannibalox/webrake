import subprocess
import json

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
        self.Height = ""
        self.Width = ""
        self.KeepAspectRatio = None
        self.Modulus = ""
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
        self.DisplayWidth = ""
        self.PixelAspect = ""

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
        self.Anamorphic = "auto"

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

        basicOptList = [ # A list of options and/or flags that don't require any special manipulation
            # If a third element exists, the option is a flag and doesn't require a parameter
            ['-i', self.Input],
            ['-o', self.Output],
            ['-m', self.IncludeChapters, True],
            ['--detelecine', self.Detelecine, True],
            ['--deinterlace', self.Deinterlace, True],
            ['-s', self.SubtitleUse],
            ['-q', self.Quality],
            ['-E', self.AudioEncoder],
            ['-r', self.FrameRate],
            ['-l', self.Hieght],
            ['-w', self.Width],
            ['--keep-display-aspect', self.KeepAspectRatio, True],
            ['--modulus', self.Modulus],
            ['--x264-preset', self.x264Preset],
            ['--x264-tune', self.x264Tune],
            ['-x', self.x264opts],
            ['--display-width', self.DisplayWidth],
            ['--pixel-aspect', self.PixelAspect]]
        for opt in basicOptList:
            if opt[1]:
                if len(opt) == 2:
                    retArray += [opt[0], opt[1]]
                else:
                    retArray += [opt[0]]
        if self.Crop:
            retArray += ['--crop', ':'.join(self.Crop)]
        if self.AudioUse:
            retArray += ['-a', self.AudioUse]
        if self.Title:
            if self.Title == HandBrakeOptions.MAIN_FEATURE:
                retArray += [HandBrakeOptions.MAIN_FEATURE]
            else:
                retArray += ['-t', self.Title]
        if self.Duration:
            retArray += ["--start-at", "duration:%s" % self.Duration[0], "--stop-at", "duration:%s" % self.Duration[1]]
        if self.Anamorphic:
            retArray += ['--%s-anamorphic' % self.Anamorphic.lower()]
        retArray += ['-e', 'x264']
        if self.AddtlOpts:
            retArray += self.AddtlOpts.split(' ') # Can't handle quotes for right now
        return retArray

class HandBrakeCLI:
    def __init__(self):
        self.HandBrakePath = "HandBrakeCLI"
        self.Options = HandBrakeOptions()
        
    def scan(self):
        scanStrings = subprocess.Popen([self.HandBrakePath, "--main-feature", "-i", self.Options.Input, "-t", "0", "-v", "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        return scanStrings

    def encode(self):
        sp = subprocess.Popen([self.HandBrakePath] + self.Options.toArgArray(), stdout= subprocess.PIPE, stderr= subprocess.PIPE)
        return sp

def main():
    hb = HandBrakeCLI()
    hb.Options.setDefaults()
    print(hb.Options.toJSON())
    hb.Options.fromJSON(hb.Options.toJSON())

if __name__ == '__main__': 
    main()
