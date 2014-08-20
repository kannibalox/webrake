import ConfigParser
import sys

class Conf(object):
    pass

def loadSettings():
    defaults = { 'PreviewLength': 30,
                 'WebHost': '127.0.0.1',
                 'Database': 'WebRake.db',
                 }
    conf = ConfigParser.RawConfigParser(defaults)
    conf.read('WebRake.cfg')
    globals()['PreviewLength'] = conf.get('Main', 'PreviewLength')
    globals()['Database'] = conf.get('Main', 'Database')
    globals()['WebHost'] = conf.get('Main', 'WebHost')
    globals()['SelectorRoot'] = conf.get('Main', 'SelectorRoot')
    globals()['ExportDirectory'] = conf.get('Main', 'ExportDirectory')
    globals()['JobsDirectory'] = conf.get('Main', 'JobsDirectory')

def get(item):
    return getattr(Conf, item)
