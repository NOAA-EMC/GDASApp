#!/usr/bin/env python3
import argparse
import os
import subprocess
from gen_bufr2ioda_json import gen_bufr_json
from wxflow import Logger, cast_strdict_as_dtypedict
from wxflow import add_to_datetime, to_timedelta

# Initialize root logger
logger = Logger('run_bufr2ioda.py', level='INFO', colored_log=True)

def bufr2ioda(CDATE, RUN, DMPDIR, config_template_dir, COM_OBS):
    logger.info(f"Process {CDATE} {RUN} from {DMPDIR} to {COM_OBS} using {config_template_dir}")

    # Derived parameters
    PDY = CDATE[:8]
    cyc = CDATE[8:10]

    config = cast_strdict_as_dtypedict(os.environ)
    config['current_cycle'] = add_to_datetime(config['PDY'], to_timedelta(f"{config['cyc']}H"))

    # Get gdasapp root directory
    DIR_ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../.."))
    USH_IODA = os.path.join(DIR_ROOT, "ush", "ioda", "bufr2ioda")
    BUFRYAMLGEN = os.path.join(USH_IODA, "gen_bufr2ioda_yaml.py")

    # Create output directory if it doesn't exist
    os.makedirs(COM_OBS, exist_ok=True)

    # Specify observation types to be processed by a script
    BUFR_py = ["satwind_amv_goes"]

    for obtype in BUFR_py:
        print(f"Processing {obtype}...")
        json_output_file = os.path.join(COM_OBS, f"{obtype}_{PDY}{cyc}.json")
        template = config_template_dir + '/bufr2ioda_' + obtype + '.json'
        gen_bufr_json(config, template, json_output_file)

        # Use the converter script for the ob type

        bufr2iodapy = USH_IODA + '/bufr2ioda_' + obtype + ".py"
        subprocess.run(["python3", bufr2iodapy, "-c", json_output_file], check=True)

        # Check if the converter was successful
        if os.path.exists(json_output_file):
            os.remove(json_output_file)
        else:
            print(f"Problem running converter script for {obtype}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert bufr dump file to ioda format')
    parser.add_argument('CDATE', type=str, help='YYYYMMDDHH date to process')
    parser.add_argument('RUN', type=str, help='dump to process, either gdas or gdas')
    parser.add_argument('DMPDIR', type=str, help='path to bufr dump files')
    parser.add_argument('config_template_dir', type=str, help='path to templates')
    parser.add_argument('COM_OBS', type=str, help='path to output ioda format dump files')
    args = parser.parse_args()
    bufr2ioda(args.CDATE, args.RUN, args.DMPDIR, args.config_template_dir, args.COM_OBS)

