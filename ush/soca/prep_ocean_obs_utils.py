#!/usr/bin/env python3
import os
import fnmatch
import subprocess
from wxflow import FileHandler, Logger, YAMLFile

logger = Logger()

# finds files in DMPDIR matching the regex in an obtype's preobs config,
# copies them to DATA, and returns a list of the files so handled


def obs_fetch(config, task_config, obsprep_space, cycles):

    DMPDIR = config.DMPDIR
    COMIN_OBS = config.COMIN_OBS

    RUN = task_config.RUN
    PDY = task_config.PDY
    cyc = task_config.cyc

    subdir = obsprep_space['dmpdir subdir']
    dumpdir_regex = obsprep_space['dmpdir regex']
    matching_files = []
    file_copy = []

    for cycle in cycles:

        PDY = cycle.strftime('%Y%m%d')
        cyc = cycle.strftime('%H')

        full_input_dir = os.path.join(DMPDIR, f"{RUN}.{PDY}", cyc, subdir)

        # TODO: check the existence of this
        logger.info(f"full_input_dir: {full_input_dir}")

        for root, _, files in os.walk(full_input_dir):
            for filename in fnmatch.filter(files, dumpdir_regex):
                target_file = f"{PDY}{cyc}-{filename}"
                matching_files.append((full_input_dir, filename, target_file, f"{PDY}{cyc}"))

    for full_input_dir, filename, target_file, _ in matching_files:
        file_path = os.path.join(full_input_dir, filename)
        file_destination = os.path.join(COMIN_OBS, target_file)
        file_copy.append([file_path, file_destination])

    logger.info(f"file_copy: {file_copy}")
    logger.info(f"matching_files: {matching_files}")

    FileHandler({'copy': file_copy}).sync()

    # return the modified file names for the IODA converters
    return [(f[2], f[3]) for f in matching_files]


def run_netcdf_to_ioda(obsspace_to_convert, OCNOBS2IODAEXEC):
    logger.info(f"running run_netcdf_to_ioda on {obsspace_to_convert['name']}")
    iodaYamlFilename = obsspace_to_convert['conversion config file']
    try:
        subprocess.run([OCNOBS2IODAEXEC, iodaYamlFilename], check=True)
        logger.info(f"ran ioda converter on obs space {obsspace_to_convert['name']} successfully")
        return 0
    except subprocess.CalledProcessError as e:
        logger.warning(f"ioda converter failed with error {e}, \
            return code {e.returncode}")
        return e.returncode


def run_bufr_to_ioda(obsspace_to_convert):
    logger.info(f"running run_bufr_to_ioda on {obsspace_to_convert['name']}")
    bufrconv_yaml = obsspace_to_convert['conversion config file']
    bufrconv_config = YAMLFile(bufrconv_yaml)
    bufr2iodapy = obsspace_to_convert['bufr2ioda converter']
    obtype = obsspace_to_convert['name']

    for cycle, input_file, output_file in obsspace_to_convert['bufrconv files']:
        bufrconv_config['input_file'] = input_file
        bufrconv_config['output_file'] = output_file
        bufrconv_config['cycle_datetime'] = cycle
        config_filename = f"{cycle}.{bufrconv_yaml}"
        bufrconv_config.save(config_filename)
        try:
            subprocess.run(['python', bufr2iodapy, '-c', config_filename], check=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"bufr2ioda converter failed with error  >{e}<, \
                return code {e.returncode}")
