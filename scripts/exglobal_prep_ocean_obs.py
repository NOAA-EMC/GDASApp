#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# Pepares observations for marine DA
from datetime import datetime, timedelta
import logging
import os
import prep_marine_obs
import subprocess
from wxflow import YAMLFile, save_as_yaml

# set up logger
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

cyc = os.getenv('cyc')
PDY = os.getenv('PDY')

# TODO (AFE): ideally this should be an env var
obsprocexec = "/scratch1/NCEPDEV/da/Andrew.Eichmann/fv3gfs/newoceaanobs/global-workflow/sorc/gdas.cd/build/bin/gdas_obsprovider2ioda.x"

logging.info('hippogriff')
print('jangle')

# set the window times
cdateDatetime = datetime.strptime(PDY + cyc, '%Y%m%d%H')
windowBeginDatetime = cdateDatetime - timedelta(hours=3)
windowEndDatetime = cdateDatetime + timedelta(hours=3)
windowBegin = windowBeginDatetime.strftime('%Y-%m-%dT%H:%M:%SZ')
windowEnd = windowEndDatetime.strftime('%Y-%m-%dT%H:%M:%SZ')

OBS_YAML = os.getenv('OBS_YAML')
obsConfig = YAMLFile(OBS_YAML)

# TODO (AFE): set dynamically, obvs
obsprocConfig = YAMLFile('/scratch1/NCEPDEV/da/Andrew.Eichmann/fv3gfs/newoceaanobs/global-workflow/sorc/gdas.cd/parm/soca/obsproc/obsproc_config.yaml')

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

