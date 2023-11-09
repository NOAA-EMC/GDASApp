#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# Pepares observations for marine DA
import os
from wxflow import YAMLFile, save_as_yaml
import prep_marine_obs
import logging
import subprocess

# set up logger
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

# TODO (AFE): ideally this should be an env var
obsprocexec = "/scratch1/NCEPDEV/da/Andrew.Eichmann/fv3gfs/newoceaanobs/global-workflow/sorc/gdas.cd/build/bin/gdas_obsprovider2ioda.x"

# TODO (AFE): set dynamically, obvs
windowBegin = '2018-04-15T06:00:00Z'
windowEnd = '2018-04-15T12:00:00Z'

OBS_YAML = os.getenv('OBS_YAML')
obsConfig = YAMLFile(OBS_YAML)
print(obsConfig)

# TODO (AFE): set dynamically, obvs
obsprocConfig = YAMLFile('/scratch1/NCEPDEV/da/Andrew.Eichmann/fv3gfs/newoceaanobs/global-workflow/sorc/gdas.cd/parm/soca/obsproc/obsproc_config.yaml')
print(obsprocConfig)

for observer in obsConfig['observers']:

    obsSpaceName = observer['obs space']['name']
    print(f"obsSpaceName: {obsSpaceName}")

    for observation in obsprocConfig['observations']:
        
        obsprocSpace = observation['obs space']
        obsprocSpaceName = obsprocSpace['name']

        if obsprocSpaceName == obsSpaceName:

           matchingFiles = prep_marine_obs.obs_fetch(obsprocSpace)
           obsprocSpace['input files'] = matchingFiles
           obsprocSpace['window begin'] = windowBegin 
           obsprocSpace['window end'] = windowEnd

           iodaYamlFilename = obsprocSpaceName + '2ioda.yaml'
           save_as_yaml(obsprocSpace, iodaYamlFilename)

           subprocess.run([obsprocexec, iodaYamlFilename], check=True)

#        else:
#           print(f"WARNING: obsSpaceName {obsSpaceName} not found in OBSPROC_YAML, skipping")

