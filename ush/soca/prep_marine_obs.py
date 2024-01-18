#!/usr/bin/env python3

from wxflow import FileHandler
import os
import fnmatch


DMPDIR = os.getenv('DMPDIR')
cyc = os.getenv('cyc')
PDY = os.getenv('PDY')
RUN = os.getenv('RUN')
COMIN_OBS = os.getenv('COMIN_OBS')

cycDir = os.path.join(DMPDIR, RUN + '.' + str(PDY), str(cyc))


def obs_fetch(obsprepSpace):

    subDir = obsprepSpace['dmpdir subdir']
    filepattern = obsprepSpace['dmpdir regex']

    dataDir = os.path.join(cycDir, subDir)
    # TODO: check the existence of this
    print('dataDir:', dataDir)
    matchingFiles = []

    for root, _, files in os.walk(dataDir):
        for filename in fnmatch.filter(files, filepattern):
            matchingFiles.append(filename)

    obsCopy = []
    for obsSource in matchingFiles:
        obsPath = os.path.join(dataDir, obsSource)
        obsDestination = os.path.join(COMIN_OBS, obsSource)
        obsCopy.append([obsPath, obsDestination])

    print(f"obsCopy: {obsCopy}")
    print(f"matchingFiles: {matchingFiles}")

    FileHandler({'copy': obsCopy}).sync()

    return matchingFiles
