import ConfigParser

defaults = {'PreviewLength' : 30}

conf = ConfigParser.RawConfigParser(defaults)
conf.read('WebRake.cfg')
