#!/usr/bin/env python3

import os
import fnmatch
import subprocess
from wxflow import FileHandler, Logger

logger = Logger()

DMPDIR = os.getenv('DMPDIR')
cyc = os.getenv('cyc')
PDY = os.getenv('PDY')
RUN = os.getenv('RUN')
COMIN_OBS = os.getenv('COMIN_OBS')
OCNOBS2IODAEXEC = os.getenv('OCNOBS2IODAEXEC')

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

def run_netcdf_to_ioda(obsspace_to_convert):
    print("obsspace_to_convert:", obsspace_to_convert['name'])
    iodaYamlFilename = obsspace_to_convert['conversion config file']
    try:
        subprocess.run([OCNOBS2IODAEXEC, iodaYamlFilename], check=True)
        logger.info(f"ran ioda converter on obs space {obsspace_to_convert['name']} successfully")
        return 0
    except subprocess.CalledProcessError as e:
        logger.warning(f"ioda converter failed with error {e}, \
            return code {e.returncode}")
        return e.returncode


def bufr2ioda(obtype, PDY, cyc, RUN, COMIN_OBS, COMOUT_OBS):
    logger.info(f"Process {obtype} for {RUN}.{PDY}/{cyc} from {COMIN_OBS} to {COMIN_OBS}")

    # Load configuration
    config = {
        'RUN': RUN,
        'current_cycle': cdateDatetime,
        'DMPDIR': COMIN_OBS,
        'COM_OBS': COMIN_OBS,
    }

    json_output_file = os.path.join(COMIN_OBS, f"{obtype}_{datetime_to_YMDH(cdateDatetime)}.json")
    filename = 'bufr2ioda_' + obtype + '.json'
    template = os.path.join(JSON_TMPL_DIR, filename)

    # Generate cycle specific json from TEMPLATE
    gen_bufr_json(config, template, json_output_file)

    bufr2iodapy = BUFR2IODA_PY_DIR + '/bufr2ioda_' + obtype + '.py'
    logger.info(f"BUFR2IODA python scripts: {bufr2iodapy}")

    try:
        subprocess.run(['python', bufr2iodapy, '-c', json_output_file, '-v'])
        logger.info(f"BUFR2IODA python API converter on obs space {obtype} ran successfully")
    except subprocess.CalledProcessError as e:
        logger.info(f"BUFR2IODA python API converter failed with error {e}, \
            return code {e.returncode}")
        #return e.returncode
        return e

def run_bufr_to_ioda(obsspace_to_convert):
    print("obsspace_to_convert:", obsspace_to_convert['name'])
    json_output_file = obsspace_to_convert['conversion config file']
    bufr2iodapy = obsspace_to_convert['bufr2ioda converter']
    try:
        subprocess.run(['python', bufr2iodapy, '-c', json_output_file, '-v'], check=True)
        logger.info(f"ran ioda converter on obs space {obsspace_to_convert['name']} successfully")
        return 0
    except subprocess.CalledProcessError as e:
        logger.warning(f"bufr2ioda converter failed with error {e}, \
            return code {e.returncode}")
        #return e.returncode
        #return e
        return -1

