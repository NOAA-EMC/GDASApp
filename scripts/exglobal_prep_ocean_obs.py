#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# Prepares observations for marine DA
from datetime import datetime, timedelta
from multiprocessing import Process
import os
from pathlib import Path
import subprocess
from soca import prep_marine_obs
from wxflow import (
    add_to_datetime,
    datetime_to_YMDH,
    FileHandler,
    Logger,
    save_as_yaml,
    to_timedelta,
    YAMLFile
)
# from gen_bufr2ioda_json import gen_bufr_json

logger = Logger()

cyc = os.getenv('cyc')
PDY = os.getenv('PDY')
RUN = os.getenv('RUN')
COMIN_OBS = os.getenv('COMIN_OBS')

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

# BUFR2IODA json and python scripts
JSON_TMPL_DIR = os.getenv('JSON_TMPL_DIR')
BUFR2IODA_PY_DIR = os.getenv('BUFR2IODA_PY_DIR')

if os.path.exists(OBSPREP_YAML):
    obsprepConfig = YAMLFile(OBSPREP_YAML)
else:
    logger.critical(f"OBSPREP_YAML file {OBSPREP_YAML} does not exist")
    raise FileNotFoundError

if not os.path.exists(COMOUT_OBS):
    os.makedirs(COMOUT_OBS)


# def bufr2ioda(obtype, PDY, cyc, RUN, COMIN_OBS, COMOUT_OBS):
#     logger.info(f"Process {obtype} for {RUN}.{PDY}/{cyc} from {COMIN_OBS} to {COMIN_OBS}")
#
#     # Load configuration
#     config = {
#         'RUN': RUN,
#         'current_cycle': cdateDatetime,
#         'DMPDIR': COMIN_OBS,
#         'COM_OBS': COMIN_OBS,
#     }
#
#     json_output_file = os.path.join(COMIN_OBS, f"{obtype}_{datetime_to_YMDH(cdateDatetime)}.json")
#     filename = 'bufr2ioda_' + obtype + '.json'
#     template = os.path.join(JSON_TMPL_DIR, filename)
#
#     # Generate cycle specific json from TEMPLATE
#     gen_bufr_json(config, template, json_output_file)
#
#     bufr2iodapy = BUFR2IODA_PY_DIR + '/bufr2ioda_' + obtype + '.py'
#     logger.info(f"BUFR2IODA python scripts: {bufr2iodapy}")
#
#     try:
#         subprocess.run(['python', bufr2iodapy, '-c', json_output_file, '-v'])
#         logger.info(f"BUFR2IODA python API converter on obs space {obtype} ran successfully")
#     except subprocess.CalledProcessError as e:
#         logger.info(f"BUFR2IODA python API converter failed with error {e}, \
#             return code {e.returncode}")
#         return e.returncode
#

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
                outputFilename = f"{RUN}.t{cyc}z.{obs_space_name}.{PDY}{cyc}.nc4"
                obsprepSpace['output file'] = outputFilename

                if obsprepSpace['type'] == 'bufr':
                    logger.warning("bufr processing is not working yet")
#                    bufr2ioda(obsprepSpaceName, PDY, cyc, RUN, COMIN_OBS, COMIN_OBS)
#                    files_to_save.append([obsprepSpace['output file'],
#                                          os.path.join(COMOUT_OBS, obsprepSpace['output file'])])
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
# TODO(AFE): add return value checking
for process in processes:
    process.join()

# TODO(AFE): Find a better way to do the "no file found" exception handling -
# this way make individual calls to FileHandler for each file, instead of
# batching them.
for file_to_save in files_to_save:
    try:
        FileHandler({'copy': [file_to_save]}).sync()
    except OSError:
        logger.warning(f"Obs file {file_to_save} not found, possible IODA converter failure)")
        continue
