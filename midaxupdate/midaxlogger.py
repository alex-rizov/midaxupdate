import logging.config
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from midaxupdate.stackdriver_logger import StackdriverLogger

class MidaxLogger(object):
    __logger = None

    @classmethod
    def initialize(cls, format='%(asctime)s [%(filename)s:%(lineno)s - %(funcName)20s() %(levelname)s] %(message)s', level=logging.DEBUG, file = "app/log/logs.log", stackdriver_creds = None):
        if cls.__logger is not None:
            return
        logging.basicConfig(format=format,
                            level=level)        
        logger = logging.getLogger("controller")
        os.makedirs(os.path.dirname(file), exist_ok=True)
        logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
        handler = TimedRotatingFileHandler(file, when = 'midnight', backupCount=30)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(format)  
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        if stackdriver_creds is not None and os.path.isfile(os.path.join(stackdriver_creds, 'credentials.json')):
            try:
                logger.addHandler(StackdriverLogger(stackdriver_creds).get_default_handler())
            except Exception:
                logger.info('Could not connect to Google Cloud logging.')
        else:
            logger.error('Can not load Google Cloud logging credentials from {}.'.format(os.path.join(stackdriver_creds, 'credentials.json')))
        cls.__logger = logger

    @classmethod
    def midaxlogger(cls):
        return cls.__logger

def get_logger():
    return MidaxLogger.midaxlogger()