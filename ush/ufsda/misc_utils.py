import logging
import os
import subprocess


scheduler = {
    'orion': 'slurm',
    'hera': 'slurm',
}


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


def create_batch_job(job_config, working_dir, exe_path, yaml_path):
    """
    create a batch job submission shell script
    """
    # open up a file for writing
    batch_script = os.path.join(working_dir, 'submit_job.sh')
    with open(batch_script, 'w') as f:
        f.write('#!/bin/bash\n')
        if scheduler[job_config['machine']] == 'slurm':
            f.write('#SBATCH -J GDASApp\n')
            f.write('#SBATCH -o GDASApp.o%J\n')
            f.write(f"#SBATCH -A {job_config['account']}\n")
            f.write(f"#SBATCH -q {job_config['queue']}\n")
            f.write(f"#SBATCH -p {job_config['partition']}\n")
            f.write(f"#SBATCH --ntasks={job_config['ntasks']}\n")
            f.write(f"#SBATCH --cpus-per-task={job_config['cpus-per-task']}\n")
            f.write(f"#SBATCH --exclusive\n")
            f.write(f"#SBATCH -t {job_config['walltime']}\n")
        f.write(f"module use {job_config['modulepath']}\n")
        f.write(f"module load GDAS/{job_config['machine']}\n")
        f.write(f"cd {working_dir}\n")
        if scheduler[job_config['machine']] == 'slurm':
            f.write(f"srun -n $SLURM_NTASKS {exe_path} {yaml_path}\n")
    logging.info(f"Wrote batch submission script to {batch_script}")
    return batch_script


def submit_batch_job(job_config, working_dir, job_script):
    """
    submit a batch job
    """
    if scheduler[job_config['machine']] == 'slurm':
        subprocess.Popen(f"sbatch {job_script}", cwd=working_dir, shell=True)
