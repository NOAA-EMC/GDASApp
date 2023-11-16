#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
from gen_bufr2ioda_json import gen_bufr_json
from wxflow import (Logger, Executable, cast_as_dtype, logit,
                    to_datetime, datetime_to_YMDH, Task, rm_p)

# Initialize root logger
logger = Logger('run_bufr2ioda.py', level='INFO', colored_log=True)


@logit(logger)
def bufr2ioda(current_cycle, RUN, DMPDIR, config_template_dir, COM_OBS):
    logger.info(f"Process {current_cycle} {RUN} from {DMPDIR} to {COM_OBS} using {config_template_dir}")

    # Get gdasapp root directory
    DIR_ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../.."))
    USH_IODA = os.path.join(DIR_ROOT, "ush", "ioda", "bufr2ioda")

    # Create output directory if it doesn't exist
    os.makedirs(COM_OBS, exist_ok=True)

    # Load configuration
    config = {
        'RUN': RUN,
        'current_cycle': current_cycle,
        'DMPDIR': DMPDIR,
        'COM_OBS': COM_OBS
    }

    # Specify observation types to be processed by a script

    BUFR_py = ["satwind_amv_ahi", "satwind_amv_goes", "satwind_scat", "adpupa_prepbufr", "adpsfc_prepbufr", "sfcshp_prepbufr"]

    for obtype in BUFR_py:
        logger.info(f"Convert {obtype}...")
        json_output_file = os.path.join(COM_OBS, f"{obtype}_{datetime_to_YMDH(current_cycle)}.json")
        filename = 'bufr2ioda_' + obtype + '.json'
        template = os.path.join(config_template_dir, filename)
        gen_bufr_json(config, template, json_output_file)

        # Use the converter script for the ob type
        bufr2iodapy = USH_IODA + '/bufr2ioda_' + obtype + ".py"
        cmd = Executable(bufr2iodapy)
        cmd.add_default_arg('-c')
        cmd.add_default_arg(json_output_file)
        logger.info(f"Executing {cmd}")
        cmd()

        # Check if the converter was successful
        if os.path.exists(json_output_file):
            rm_p(json_output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert bufr dump file to ioda format')
    parser.add_argument('current_cycle', help='current cycle to process', type=lambda dd: to_datetime(dd))
    parser.add_argument('RUN', type=str, help='dump to process, either gdas or gdas')
    parser.add_argument('DMPDIR', type=Path, help='path to bufr dump files')
    parser.add_argument('config_template_dir', type=Path, help='path to templates')
    parser.add_argument('COM_OBS', type=Path, help='path to output ioda format dump files')
    args = parser.parse_args()
    bufr2ioda(args.current_cycle, args.RUN, args.DMPDIR, args.config_template_dir, args.COM_OBS)
