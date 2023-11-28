#!/usr/bin/env python3
import argparse
import glob
import multiprocessing as mp
import os
import shutil
from itertools import repeat
from pathlib import Path
from gen_bufr2ioda_json import gen_bufr_json
from gen_bufr2ioda_yaml import gen_bufr_yaml
from wxflow import (Logger, Executable, cast_as_dtype, logit,
                    to_datetime, datetime_to_YMDH, Task, rm_p)

# Initialize root logger
logger = Logger('run_bufr2ioda.py', level='INFO', colored_log=True)

# get parallel processing info
num_cores = mp.cpu_count()


def mp_bufr_converter(exename, configfile):
    cmd = Executable(exename)
    filetype = Path(configfile).suffix
    if filetype == '.json':
        cmd.add_default_arg('-c')
    cmd.add_default_arg(configfile)
    logger.info(f"Executing {cmd}")
    cmd()


@logit(logger)
def bufr2ioda(current_cycle, RUN, DMPDIR, config_template_dir, COM_OBS):
    logger.info(f"Process {current_cycle} {RUN} from {DMPDIR} to {COM_OBS} using {config_template_dir}")

    # Get gdasapp root directory
    DIR_ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../.."))
    USH_IODA = os.path.join(DIR_ROOT, "ush", "ioda", "bufr2ioda")
    BIN_GDAS = os.path.join(DIR_ROOT, "build", "bin")
    DATA = os.getcwd()

    # Create output directory if it doesn't exist
    os.makedirs(COM_OBS, exist_ok=True)

    # Load configuration
    config = {
        'RUN': RUN,
        'current_cycle': current_cycle,
        'DMPDIR': DMPDIR,
        'COM_OBS': COM_OBS,
        'PDY': current_cycle.strftime('%Y%m%d'),
        'cyc': current_cycle.strftime('%H'),
    }

    # copy necessary fix files to runtime directory
    fix_files = ["atms_beamwidth.txt",
                 "amsua_metop-c_v2.ACCoeff.nc"
                 ]
    for fix_file in fix_files:
        shutil.copy(os.path.join(config_template_dir, fix_file), os.path.join(DATA, fix_file))

    # Specify observation types to be processed by a script
    BUFR_py_files = glob.glob(os.path.join(USH_IODA, 'bufr2ioda_*.py'))
    BUFR_py_files = [os.path.basename(f) for f in BUFR_py_files]
    BUFR_py = [f.replace('bufr2ioda_', '').replace('.py', '') for f in BUFR_py_files]

    config_files = []
    exename = []
    for obtype in BUFR_py:
        logger.info(f"Convert {obtype}...")
        json_output_file = os.path.join(DATA, f"{obtype}_{datetime_to_YMDH(current_cycle)}.json")
        filename = 'bufr2ioda_' + obtype + '.json'
        template = os.path.join(config_template_dir, filename)
        gen_bufr_json(config, template, json_output_file)

        # Use the converter script for the ob type
        bufr2iodapy = USH_IODA + '/bufr2ioda_' + obtype + ".py"

        # append the values to the lists
        config_files.append(json_output_file)
        exename.append(bufr2iodapy)

        # Check if the converter was successful
        # if os.path.exists(json_output_file):
        #     rm_p(json_output_file)

    # Specify observation types to be processed by the bufr2ioda executable
    BUFR_yaml_files = glob.glob(os.path.join(config_template_dir, '*.yaml'))
    BUFR_yaml_files = [os.path.basename(f) for f in BUFR_yaml_files]
    BUFR_yaml = [f.replace('bufr2ioda_', '').replace('.yaml', '') for f in BUFR_yaml_files]

    for obtype in BUFR_yaml:
        logger.info(f"Convert {obtype}...")
        yaml_output_file = os.path.join(DATA, f"{obtype}_{datetime_to_YMDH(current_cycle)}.yaml")
        filename = 'bufr2ioda_' + obtype + '.yaml'
        template = os.path.join(config_template_dir, filename)
        gen_bufr_yaml(config, template, yaml_output_file)

        # use the bufr2ioda executable for the ob type
        bufr2iodaexe = BIN_GDAS + '/bufr2ioda.x'

        # append the values to the lists
        config_files.append(yaml_output_file)
        exename.append(bufr2iodaexe)

        # Check if the converter was successful
        # if os.path.exists(yaml_output_file):
        #     rm_p(yaml_output_file)

        # run everything in parallel
    with mp.Pool(num_cores) as pool:
        pool.starmap(mp_bufr_converter, zip(exename, config_files))

    config_files = []
    exename = []
    # Specify observation types to be processed by a script with combined methods
    script_type = 'bufr2ioda_combine_'
    BUFR_combine_files = glob.glob(os.path.join(USH_IODA, script_type + '*.py'))
    BUFR_combine_files = [os.path.basename(f) for f in BUFR_combine_files]
    BUFR_combine = [f.replace(script_type, '').replace('.py', '') for f in BUFR_combine_files]

    for obtype in BUFR_combine:
        logger.info(f"Convert {obtype}...")
        json_output_file = os.path.join(DATA, f"{obtype}_{datetime_to_YMDH(current_cycle)}.json")
        filename = 'bufr2ioda_' + obtype + '.json'
        template = os.path.join(config_template_dir, filename)
        gen_bufr_json(config, template, json_output_file)

        # Use the converter script for the ob type
        bufr2iodapy = os.path.join(USH_IODA, script_type + obtype + ".py")

        # append the values to the lists
        config_files.append(json_output_file)
        exename.append(bufr2iodapy)

    # run everything in parallel
    with mp.Pool(num_cores) as pool:
        pool.starmap(mp_bufr_converter, zip(exename, config_files))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert bufr dump file to ioda format')
    parser.add_argument('current_cycle', help='current cycle to process', type=lambda dd: to_datetime(dd))
    parser.add_argument('RUN', type=str, help='dump to process, either gdas or gdas')
    parser.add_argument('DMPDIR', type=Path, help='path to bufr dump files')
    parser.add_argument('config_template_dir', type=Path, help='path to templates')
    parser.add_argument('COM_OBS', type=Path, help='path to output ioda format dump files')
    args = parser.parse_args()
    bufr2ioda(args.current_cycle, args.RUN, args.DMPDIR, args.config_template_dir, args.COM_OBS)
