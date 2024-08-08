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


def run_diff(file1, file2):
    # log this....
    # print("running diff on: ")
    # print("file 1 = ", file1)
    # print("file 2 = ", file2)

    try:
        # Run the diff command
        result = subprocess.run(
            ['diff', file1, file2],
            capture_output=True, text=True, check=False
        )

        # Check if diff command succeeded (return code 0)
        if result.returncode == 0:
            print("Files are identical.")
        elif result.returncode == 1:
            # Print the difference if files are different
            print("Files are different:")
            print(result.stdout)
        else:
            print("Error occurred while running diff command.")
            print(result.stderr)

    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")

    return result.returncode


def run_diff_script_inline(file1, file2, script_content):
    try:
        # Create a temporary script file with the provided content
        script_path = '/tmp/temp_script.sh'
        with open(script_path, 'w') as f:
            f.write(script_content)

        # Make the script executable
        subprocess.run(['chmod', '+x', script_path], check=True)

        # Construct the command to run the temporary script
        command = [script_path, file1, file2]

        # Run the script and capture the output
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)

        # Return the output of the script (which is assumed to be the result of the diff)
        return result.stdout

    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        # Clean up: delete the temporary script file
        try:
            subprocess.run(['rm', '-f', script_path])
        except Exception as e:
            print(f"Error cleaning up temp script: {e}")


def Compute_sequenceNumber(lon):
    lon_u, seqNum = np.unique(lon, return_inverse=True)
    seqNum = seqNum.astype(np.int32)
    # logger.debug(f"Len of Sequence Number: {len(seqNum)}")
    return seqNum


def nc_diff(file1, file2):
    try:
        script_content = '''
#!/bin/bash
diff <(ncdump "$1"| sed '1d') <(ncdump "$2"|sed '1d')
'''

        # Create a temporary script file with the provided content
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_script:
            temp_script.write(script_content.lstrip())  # Remove leading indentation

        # Make the script executable
        os.chmod(temp_script.name, 0o755)  # Make it executable for owner

        # Construct the command to run the temporary script
        command = ['bash', temp_script.name, file1, file2]

        # result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return result.returncode
        # return result.stdout

    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        # print(f"Script stderr: {e.stderr}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        # Clean up: delete the temporary script file
        try:
            os.remove(temp_script.name)
        except Exception as e:
            print(f"Error cleaning up temp script: {e}")
