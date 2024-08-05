import os
import sys
import argparse
import subprocess
import numpy as np
import tempfile
# import logging
# import colorlog


# def get_logger(name, level=logging.DEBUG):
    # logger = logging.getLogger(name)
    # logger.setLevel(level)
# 
    # handler = colorlog.StreamHandler()
    # handler.setFormatter(colorlog.ColoredFormatter(
        # '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
        # log_colors={
            # 'DEBUG': 'cyan',
            # 'INFO': 'green',
            # 'WARNING': 'yellow',
            # 'ERROR': 'red',
            # 'CRITICAL': 'red,bg_white',
        # },
        # reset=True,
        # style='%'
    # ))
# 
    # logger.addHandler(handler)
    # return logger



def ParseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', \
        type=str, help='Input JSON or YAML configuration', required=True)
    parser.add_argument('-l', '--log_file', \
        type=str, help='Output file for testing ioda variables')
    parser.add_argument('-t', '--test', \
        type=str, help='Input test reference file')
    # parser.add_argument('-v', '--verbose', \
        # help='Print debug logging information',
        # action='store_true')

    args = parser.parse_args()

    # log_level = 'DEBUG' if args.verbose else 'INFO'
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
        result = subprocess.run(['diff', file1, file2], \
            capture_output=True, text=True, check=False)

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



# to be deprecated.....
def WriteTestOutputFile(directory_path, file_name, text):

    # Check if the directory exists, create it if it doesn't
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Directory '{directory_path}' created.")

    file_path = os.path.join(directory_path, file_name)
    print(f"File '{file_path}' created.")

    with open(file_path, 'w') as file:
        for s in text:
            file.write(f"{s}\n")

    return



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

        # Check the return code of the subprocess
        # if result.returncode != 0:
            # print(f"Script exited with non-zero status: {result.returncode}")
            # return result.returncode
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




if __name__ == '__main__':


    file1 = '/scratch1/NCEPDEV/stmp2/Edward.Givelberg/RUNDIRS/GFSv17-3DVAR-C384mx025/prepoceanobs.114138/gdas.t06z.insitu_profile_argo.2021063006.nc4'
    file2 = '/scratch1/NCEPDEV/stmp2/Edward.Givelberg/RUNDIRS/GFSv17-3DVAR-C384mx025/prepoceanobs.114138/backup_gdas.t06z.insitu_profile_argo.2021063006.nc4'
    # file2 = '/scratch1/NCEPDEV/stmp2/Edward.Givelberg/RUNDIRS/GFSv17-3DVAR-C384mx025/prepoceanobs.114138/gdas.t06z.sst_viirs_npp_l3u.2021063006.nc4'


    diff_result = nc_diff(file1, file2)
    if diff_result == 0:
        print("identitcal")
    else:
        print("different")

