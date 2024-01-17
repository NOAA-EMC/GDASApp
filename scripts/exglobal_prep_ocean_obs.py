#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# Pepares observations for marine DA
from datetime import datetime, timedelta
import logging
import os
from soca import prep_marine_obs
import subprocess
from wxflow import YAMLFile, save_as_yaml, FileHandler

# TODO (AFE) figure out why logger is not logging
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
COMOUT_OBS = os.getenv('COMOUT_OBS')

OBS_YAML = os.getenv('OBS_YAML')
# this will fail with FileNotFoundError if all yaml files in OBS_YAML are not
# present in OBS_YAML_DIR
obsConfig = YAMLFile(OBS_YAML)

OBSPREP_YAML = os.getenv('OBSPREP_YAML')

if os.path.exists(OBSPREP_YAML):
    obsprepConfig = YAMLFile(OBSPREP_YAML)
else:
    print(f"CRITICAL: OBSPREP_YAML file {OBSPREP_YAML} does not exist")
    raise FileNotFoundError

filesToSave = []

# TODO (AFE): needs more error handling (missing sources, missing files)
try:
    # For each of the observation sources (observers) specificed in the OBS_YAML...
    for observer in obsConfig['observers']:

        try:
            obsSpaceName = observer['obs space']['name']
            print(f"obsSpaceName: {obsSpaceName}")
        except KeyError:
            print(f"observer: {observer}")
            print("WARNING: Ill-formed observer yaml file, skipping")
            continue  # to next observer

# ...look through the observations in OBSPREP_YAML...
        for observation in obsprepConfig['observations']:

            obsprepSpace = observation['obs space']
            obsprepSpaceName = obsprepSpace['name']

# ...for a matching name, and process the observation source
            if obsprepSpaceName == obsSpaceName:

                print(f"obsprepSpaceName: {obsSpaceName}")

                # fetch the obs files from DMPDIR to RUNDIR
                matchingFiles = prep_marine_obs.obs_fetch(obsprepSpace)

                if not matchingFiles:
                    print("WARNING: No files found for obs source , skipping")
                    break  # to next observation source in OBS_YAML

                obsprepSpace['input files'] = matchingFiles
                obsprepSpace['window begin'] = windowBegin
                obsprepSpace['window end'] = windowEnd
                outputFilename = f"gdas.t{cyc}z.{obsSpaceName}.{PDY}{cyc}.nc4"
                obsprepSpace['output file'] = outputFilename

                iodaYamlFilename = obsprepSpaceName + '2ioda.yaml'
                save_as_yaml(obsprepSpace, iodaYamlFilename)

                subprocess.run([OCNOBS2IODAEXEC, iodaYamlFilename], check=True)

                filesToSave.append([obsprepSpace['output file'],
                                    os.path.join(COMOUT_OBS, obsprepSpace['output file'])])
                filesToSave.append([iodaYamlFilename,
                                    os.path.join(COMOUT_OBS, iodaYamlFilename)])
except TypeError:
    print("CRITICAL: Ill-formed OBS_YAML or OBSPREP_YAML file, exiting")
    raise

if not os.path.exists(COMOUT_OBS):
    os.makedirs(COMOUT_OBS)

FileHandler({'copy': filesToSave}).sync()
