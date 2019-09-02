import logging
import sys

import zerorpc

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class Locker():
    def __init__(self):
        logger.info('Locking server started...')
        
    def hello(self, name):
        logger.info(f'{name} said hello.')
        return 'hello'
    
    def lock(self, filename):
        value = 2
        return value


s = zerorpc.Server(Locker())
s.bind('tcp://*:6778')
s.run()
