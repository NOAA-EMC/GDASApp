import os
import sys
import argparse
import subprocess
import numpy as np
import tempfile


def ParseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--config',
        type=str,
        help='Input JSON or YAML configuration', required=True
    )
    parser.add_argument(
        '-l', '--log_file',
        type=str,
        help='Output file for testing ioda variables'
    )
    parser.add_argument(
        '-t', '--test',
        type=str,
        help='Input test reference file'
    )

    args = parser.parse_args()
    config_file = args.config
    log_file = args.log_file
    test_file = args.test
    script_name = sys.argv[0]
    return script_name, config_file, log_file, test_file


def Compute_sequenceNumber(lon):
    lon_u, seqNum = np.unique(lon, return_inverse=True)
    seqNum = seqNum.astype(np.int32)
    # logger.debug(f"Len of Sequence Number: {len(seqNum)}")
    return seqNum


def run_diff(file1, file2, logger):
    try:
        # Run the diff command
        result = subprocess.run(
            ['diff', file1, file2],
            capture_output=True, text=True, check=False
        )

        # Check if diff command succeeded (return code 0)
        if result.returncode == 0:
            pass
        elif result.returncode == 1:
            logger.error("Files are different:")
            logger.error(f"{result.stdout}")
        else:
            logger.error("Error occurred while running diff command.")
            logger.error(f"{result.stdout}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")

    return result.returncode
