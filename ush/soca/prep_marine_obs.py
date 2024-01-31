#!/usr/bin/env python3

import os
import fnmatch
from wxflow import FileHandler, Logger

logger = Logger()

DMPDIR = os.getenv('DMPDIR')
cyc = os.getenv('cyc')
PDY = os.getenv('PDY')
RUN = os.getenv('RUN')
COMIN_OBS = os.getenv('COMIN_OBS')


def obs_fetch(obsprepSpace, cycles):

    subDir = obsprepSpace['dmpdir subdir']
    filepattern = obsprepSpace['dmpdir regex']
    matchingFiles = []
    fileCopy = []
    targetFiles = []

    for cycle in cycles:

        cycleDate = cycle.strftime('%Y%m%d')
        cycleHour = cycle.strftime('%H')

        dataDir = os.path.join(DMPDIR, RUN + '.' + cycleDate, cycleHour, subDir)

        # TODO: check the existence of this
        logger.info(f"dataDir: {dataDir}")

        for root, _, files in os.walk(dataDir):
            for filename in fnmatch.filter(files, filepattern):
                targetFile = cycleDate + cycleHour + '-' + filename
                matchingFiles.append((dataDir, filename, targetFile))

    for matchingFile in matchingFiles:
        filePath = os.path.join(matchingFile[0], matchingFile[1])
        fileDestination = os.path.join(COMIN_OBS, matchingFile[2])
        fileCopy.append([filePath, fileDestination])

    logger.info(f"fileCopy: {fileCopy}")
    logger.info(f"matchingFiles: {matchingFiles}")

    FileHandler({'copy': fileCopy}).sync()

    # return the modified file names for the IODA converters
    return [f[2] for f in matchingFiles]
