import os
import sys
import argparse
import subprocess
import numpy as np
import tempfile
import hashlib


def parse_arguments():
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
            logger.error("diff on files:")
            logger.error(f"{file1}")
            logger.error(f"{file2}")
            logger.error("Files are different:")
            logger.error(f"{result.stdout}")
        else:
            logger.error("Error occurred while running diff command.")
            logger.error(f"{result.stdout}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")

    return result.returncode


# use hash for testing;
def compute_hash(sequence, algorithm='sha256'):
    """
    Compute a hash of the given sequence using the specified algorithm.

    :param sequence: A sequence of numbers (e.g., list of integers).
    :param algorithm: The hash algorithm to use (e.g., 'sha256').
    :return: The hexadecimal digest of the hash.
    """
    # Convert the sequence to a byte string
    sequence_bytes = bytes(sequence)
    # Create a hash object
    hash_obj = hashlib.new(algorithm)
    # Update the hash object with the byte string
    hash_obj.update(sequence_bytes)
    # Return the hexadecimal digest of the hash
    return hash_obj.hexdigest()
