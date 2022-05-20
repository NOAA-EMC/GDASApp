import logging
import os
import re
import solo.date
import subprocess


scheduler = {
    'orion': 'slurm',
    'hera': 'slurm',
}


def calc_fcst_steps(fcst_step, win_length):
    """
    function to return a list of forecast steps
    for a given fcst_step (forecast step)
    and win_length (window length)
    """
    # need to get +- half of the window length
    # assumes only hours for now, probably bad...
    h = int(re.findall('PT(\\d+)H', win_length)[0])
    start = f'PT{h//2}H'
    end = f'PT{h*2}H'
    # solo has a nice utility for this
    fcst_steps = solo.date.step_sequence(start, end, fcst_step)
    return fcst_steps


def isTrue(str_in):
    """ isTrue(str_in)
    - function to translate shell variables to python logical variables
    input: str_in - string (should be like 'YES', 'TRUE', etc.)
    returns: status (logical True or False)
    """
    str_in = str_in.upper()
    if str_in in ['Y', 'YES', '.TRUE.']:
        status = True
    else:
        status = False
    return status


def create_batch_job(job_config, working_dir, executable, yaml_path):
    """
    create a batch job submission shell script
    """
    # open up a file for writing
    batch_script = os.path.join(working_dir, 'submit_job.sh')
    with open(batch_script, 'w') as f:
        f.write('#!/bin/bash\n')
        if scheduler[job_config['machine']] == 'slurm':
            sbatch = f"""#SBATCH -J GDASApp
#SBATCH -o GDASApp.o%J
#SBATCH -A {job_config['account']}
#SBATCH -q {job_config['queue']}
#SBATCH -p {job_config['partition']}
#SBATCH --ntasks={job_config['ntasks']}
#SBATCH --cpus-per-task={job_config['cpus-per-task']}
#SBATCH --exclusive
#SBATCH -t {job_config['walltime']}"""
            f.write(sbatch)
        commands = f"""
module purge
module use {job_config['modulepath']}
module load GDAS/{job_config['machine']}
cd {working_dir}
"""
        f.write(commands)
        if scheduler[job_config['machine']] == 'slurm':
            f.write(f"srun -n $SLURM_NTASKS {executable} {yaml_path}\n")
    logging.info(f"Wrote batch submission script to {batch_script}")
    return batch_script


def submit_batch_job(job_config, working_dir, job_script):
    """
    submit a batch job
    """
    if scheduler[job_config['machine']] == 'slurm':
        subprocess.Popen(f"sbatch {job_script}", cwd=working_dir, shell=True)
