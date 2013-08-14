import ConfigParser
import sys

PreviewLength = None

class Conf(object):
    pass

def loadSettings():
    defaults = { 'PreviewLength': 30,
                 'WebHost': '127.0.0.1',
                 'Database': 'WebRake.db'
                 }
    conf = ConfigParser.RawConfigParser(defaults)
    conf.read('WebRake.cfg')
    globals()['PreviewLength'] = conf.get('Main', 'PreviewLength')
    globals()['Database'] = conf.get('Main', 'Database')
    globals()['WebHost'] = conf.get('Main', 'WebHost')

def get(item):
    return getattr(Conf, item)
