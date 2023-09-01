#!/usr/bin/env python3
import os
import subprocess


def main():
    # Check command line arguments
    if len(sys.argv) != 6:
        print("usage:")
        print(f"{sys.argv[0]} YYYYMMDDHH gdas|gfs /path/to/files.bufr_d/ /path/to/templates /path/to/output.ioda/")
        sys.exit(1)

    # Input parameters
    CDATE = sys.argv[1]
    DUMP = sys.argv[2]
    DMPDIR = sys.argv[3]
    config_template_dir = sys.argv[4]
    COM_OBS = sys.argv[5]

    # Derived parameters
    PDY = CDATE[:8]
    cyc = CDATE[8:10]

    # Get gdasapp root directory
    DIR_ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../.."))
    BUFR2IODA = os.path.join(DIR_ROOT, "build", "bin", "bufr2ioda.x")
    USH_IODA = os.path.join(DIR_ROOT, "ush", "ioda", "bufr2ioda")
    BUFRYAMLGEN = os.path.join(USH_IODA, "gen_bufr2ioda_yaml.py")
    BUFRJSONGEN = os.path.join(USH_IODA, "gen_bufr2ioda_json.py")

    # Create output directory if it doesn't exist
    os.makedirs(COM_OBS, exist_ok=True)

    # Add the necessary libraries to PYTHONPATH
    PYIODALIB = os.path.join(DIR_ROOT, "build", "lib", f"python{sys.version_info.major}.{sys.version_info.minor}")
    os.environ["PYTHONPATH"] = f"{PYIODALIB}:{os.environ.get('PYTHONPATH', '')}"

    # Specify observation types to be processed by a script
    BUFR_py = ["satwind_amv_goes"]

    for obtype in BUFR_py:
        print(f"Processing {obtype}...")
        json_output_file = os.path.join(COM_OBS, f"{obtype}_{PDY}{cyc}.json")

        # Generate a JSON from the template
        subprocess.run([BUFRJSONGEN, "-t", f"{config_template_dir}/bufr2ioda_{obtype}.json", "-o", json_output_file], check=True)

        # Use the converter script for the ob type
        subprocess.run(["python3", f"{os.path.join(USH_IODA, 'bufr2ioda_' + obtype + '.py')}", "-c", json_output_file], check=True)

        # Check if the converter was successful
        if os.path.exists(json_output_file):
            os.remove(json_output_file)
        else:
            print(f"Problem running converter script for {obtype}")


if __name__ == "__main__":
    import sys
    main()
