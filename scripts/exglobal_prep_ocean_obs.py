#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# Pepares observations for marine DA
from datetime import datetime, timedelta
import logging
import os
import prep_marine_obs
import subprocess
<<<<<<< HEAD
import sys
=======
>>>>>>> develop
from wxflow import YAMLFile, save_as_yaml

# set up logger
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

cyc = os.getenv('cyc')
PDY = os.getenv('PDY')

# set the window times
cdateDatetime = datetime.strptime(PDY + cyc, '%Y%m%d%H')
windowBeginDatetime = cdateDatetime - timedelta(hours=3)
windowEndDatetime = cdateDatetime + timedelta(hours=3)
windowBegin = windowBeginDatetime.strftime('%Y-%m-%dT%H:%M:%SZ')
windowEnd = windowEndDatetime.strftime('%Y-%m-%dT%H:%M:%SZ')

OCNOBS2IODAEXEC = os.getenv('OCNOBS2IODAEXEC')

OBS_YAML = os.getenv('OBS_YAML')
# this will fail with FileNotFoundError if all yaml files in OBS_YAML are not
# present in OBS_YAML_DIR
obsConfig = YAMLFile(OBS_YAML)

OBSPROC_YAML = os.getenv('OBSPROC_YAML')
obsprocConfig = YAMLFile(OBSPROC_YAML)

# TODO (AFE): needs more error handling (missing sources, missing files)
try:
    for observer in obsConfig['observers']:

        try:
            obsSpaceName = observer['obs space']['name']
        except KeyError:
            print(f"observer: {observer}") 
            print("WARNING: Ill-formed observer yaml file, skipping")
            continue # to next observer

        print(f"obsSpaceName: {obsSpaceName}") 

        for observation in obsprocConfig['observations']:
    
            obsprocSpace = observation['obs space']
            obsprocSpaceName = obsprocSpace['name']
    
            if obsprocSpaceName == obsSpaceName:
    
                print(f"obsprocSpaceName: {obsSpaceName}")

                # fetch the obs files from DMPDIR to RUNDIR
                matchingFiles = prep_marine_obs.obs_fetch(obsprocSpace)
                obsprocSpace['input files'] = matchingFiles
                obsprocSpace['window begin'] = windowBegin
                obsprocSpace['window end'] = windowEnd
    
                iodaYamlFilename = obsprocSpaceName + '2ioda.yaml'
                save_as_yaml(obsprocSpace, iodaYamlFilename)
    
                subprocess.run([OCNOBS2IODAEXEC, iodaYamlFilename], check=True)
except TypeError: 
    sys.exit("CRITICAL: Ill-formed OBS_YAML file, exiting")
