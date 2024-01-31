#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# Prepares observations for marine DA
from datetime import datetime, timedelta
from multiprocessing import Process
import os
import subprocess
from soca import prep_marine_obs
from wxflow import YAMLFile, save_as_yaml, FileHandler, Logger

logger = Logger()

cyc = os.getenv('cyc')
PDY = os.getenv('PDY')

# Set the window times
cdateDatetime = datetime.strptime(PDY + cyc, '%Y%m%d%H')
windowBeginDatetime = cdateDatetime - timedelta(hours=3)
windowEndDatetime = cdateDatetime + timedelta(hours=3)
windowBegin = windowBeginDatetime.strftime('%Y-%m-%dT%H:%M:%SZ')
windowEnd = windowEndDatetime.strftime('%Y-%m-%dT%H:%M:%SZ')

OCNOBS2IODAEXEC = os.getenv('OCNOBS2IODAEXEC')
COMOUT_OBS = os.getenv('COMOUT_OBS')

OBS_YAML = os.getenv('OBS_YAML')

obsConfig = YAMLFile(OBS_YAML)

OBSPREP_YAML = os.getenv('OBSPREP_YAML')

if os.path.exists(OBSPREP_YAML):
    obsprepConfig = YAMLFile(OBSPREP_YAML)
else:
    logger.critical(f"OBSPREP_YAML file {OBSPREP_YAML} does not exist")
    raise FileNotFoundError


def run_netcdf_to_ioda(obsspace_to_convert):
    name, iodaYamlFilename = obsspace_to_convert
    try:
        subprocess.run([OCNOBS2IODAEXEC, iodaYamlFilename], check=True)
        logger.info(f"ran ioda converter on obs space {name} successfully")
    except subprocess.CalledProcessError as e:
        logger.info(f"ioda converter failed with error {e}, \
            return code {e.returncode}")
        return e.returncode


files_to_save = []
obsspaces_to_convert = []

try:
    for observer in obsConfig['observers']:
        try:
            obs_space_name = observer['obs space']['name']
            logger.info(f"obsSpaceName: {obs_space_name}")
        except KeyError:
            logger.warning(f"observer: {observer}")
            logger.warning("Ill-formed observer yaml file, skipping")
            continue

        # find match to the obs space from OBS_YAML in OBSPREP_YAML
        # this is awkward and unpythonic, so feel free to improve
        for observation in obsprepConfig['observations']:
            obsprepSpace = observation['obs space']
            obsprepSpaceName = obsprepSpace['name']

            if obsprepSpaceName == obs_space_name:
                logger.info(f"obsprepSpaceName: {obs_space_name}")
                pdyDatetime = datetime.strptime(PDY + cyc, '%Y%m%d%H')
                cycles = []

                try:
                    obsWindowBack = obsprepSpace['window']['back']
                    obsWindowForward = obsprepSpace['window']['forward']
                except KeyError:
                    obsWindowBack = 0
                    obsWindowForward = 0

                for i in range(-obsWindowBack, obsWindowForward + 1):
                    interval = timedelta(hours=6 * i)
                    cycles.append(pdyDatetime + interval)

                matchingFiles = prep_marine_obs.obs_fetch(obsprepSpace, cycles)

                if not matchingFiles:
                    logger.warning("No files found for obs source, skipping")
                    break

                obsprepSpace['input files'] = matchingFiles
                obsprepSpace['window begin'] = windowBegin
                obsprepSpace['window end'] = windowEnd
                outputFilename = f"gdas.t{cyc}z.{obs_space_name}.{PDY}{cyc}.nc4"
                obsprepSpace['output file'] = outputFilename

                # Skip in situ IODA conversion for now
                if obsprepSpaceName.split('_')[0] == 'insitu':
                    logger.info("Skipping insitu conversion for now")
                else:
                    iodaYamlFilename = obsprepSpaceName + '2ioda.yaml'
                    save_as_yaml(obsprepSpace, iodaYamlFilename)

                files_to_save.append([obsprepSpace['output file'],
                                      os.path.join(COMOUT_OBS, obsprepSpace['output file'])])
                files_to_save.append([iodaYamlFilename,
                                      os.path.join(COMOUT_OBS, iodaYamlFilename)])

                obsspaces_to_convert.append((obs_space_name, iodaYamlFilename))

except TypeError:
    logger.critical("Ill-formed OBS_YAML or OBSPREP_YAML file, exiting")
    raise

processes = []
for obsspace_to_convert in obsspaces_to_convert:
    process = Process(target=run_netcdf_to_ioda, args=(obsspace_to_convert,))
    process.start()
    processes.append(process)

# Wait for all processes to finish
for process in processes:
    process.join()

if not os.path.exists(COMOUT_OBS):
    os.makedirs(COMOUT_OBS)

FileHandler({'copy': files_to_save}).sync()
