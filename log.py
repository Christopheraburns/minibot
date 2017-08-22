import logging
import datetime
import time
LOGFILE='botBoot.log'

class rLog(object):

    def __init__(self, init):
        if init: #create a new log file
            logging.getLogger("botLog")
            logging.basicConfig(filename=LOGFILE, level=logging.DEBUG)
            logging.info("")
            logging.info("*******************New bot instance booting!***********************************")
            logging.info("********************************************************************************")
            logging.info("")
        else:   #write to an existing log file
            logging.getLogger("botLog")
            logging.basicConfig(filename=LOGFILE, level=logging.DEBUG)

    def LogThis(self, message):
        ts = time.time()
        logging.info(str(ts) + ":: " + message + ' \n')
        print(message)

    def LogDebug(self, message):
        ts = time.time()
        logging.debug(str(ts) + ":: " + message + ' \n')
        print("DEBUG: {}".format(message))

    def LogWarning(self, message):
        ts = time.time()
        logging.warning(str(ts) + ":: " + message + ' \n')
        print("WARNING: {}".format(message))

    def LogError(self, message):
        ts = time.time()
        logging.error(str(ts) + ":: " + message + ' \n')
        print("ERROR: {}".format(message))

    def LogCritical(self, message):
        ts = time.time()
        logging.critical(str(ts) + ":: " + message + ' \n')
        print("CRITICAL: {}".format(message))