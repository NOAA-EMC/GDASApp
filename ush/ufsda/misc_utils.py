import datetime as dt
import logging
import os
import re
import stat
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


def create_batch_job(job_config, working_dir, executable, yaml_path, single_exec=True):
    """
    create a batch job submission shell script
    """
    # open up a file for writing
    batch_script = os.path.join(working_dir, 'submit_job.sh')
    with open(batch_script, 'w') as f:
        f.write('#!/bin/bash\n')
        if scheduler[job_config['machine']] == 'slurm':
            if job_config['machine'] == 'hera':
                taskspernode = job_config.get("ntasks-per-node", 18)
            elif job_config['machine'] == 'orion':
                taskspernode = job_config.get("ntasks-per-node", 24)
            else:
                taskspernode = job_config.get("ntasks-per-node", 12)
            sbatch = f"""#SBATCH -J GDASApp
#SBATCH -o GDASApp.o%J
#SBATCH -A {job_config['account']}
#SBATCH -q {job_config['queue']}
#SBATCH -p {job_config['partition']}
#SBATCH --ntasks={job_config['ntasks']}
#SBATCH --ntasks-per-node={taskspernode}
#SBATCH --cpus-per-task=1
#SBATCH --mem=0
#SBATCH -t {job_config['walltime']}"""
            f.write(sbatch)
        commands = f"""
module purge
module use {job_config['modulepath']}
module load GDAS/{job_config['machine']}
cd {working_dir}
"""
        f.write(commands)
        if single_exec:
            # standalone jedi application
            if scheduler[job_config['machine']] == 'slurm':
                f.write(f"srun -n $SLURM_NTASKS {executable} {yaml_path}\n")
        else:
            # TODO (Guillaume): Hard coded for soca in a few places, change that
            scripts_path = os.path.join(job_config['modulepath'], '../', 'scripts')
            # run the pre/run/post scripts
            f.write(f"source load_envar.sh\n")
            f.write(f"{scripts_path}/exgdas_global_marine_analysis_prep.py\n")
            f.write(f"cd {working_dir}/analysis\n")
            f.write(f"export APRUN_OCNANAL=\"{job_config['mpiexec']} {job_config['mpinproc']} {job_config['ntasks']}\"\n")
            f.write(f"{scripts_path}/exgdas_global_marine_analysis_run.sh\n")
    logging.info(f"Wrote batch submission script to {batch_script}")

    return batch_script


def submit_batch_job(job_config, working_dir, job_script):
    """
    submit a batch job
    """
    if scheduler[job_config['machine']] == 'slurm':
        subprocess.Popen(f"sbatch {job_script}", cwd=working_dir, shell=True)


def datetime_from_cdate(cdate):
    cdate_obj = dt.datetime.strptime(cdate, "%Y%m%d%H")
    return cdate_obj


def get_env_config(component='atm'):
    # get config dict based on environment variables
    # TODO break this into component specific sections
    # datetime objects
    cdate = os.environ['PDY']+os.environ['cyc']
    valid_time = datetime_from_cdate(cdate)
    assim_freq = int(os.environ['assim_freq'])
    prev_cycle = valid_time - dt.timedelta(hours=assim_freq)
    gPDY = f"{prev_cycle.strftime('%Y%m%d')}"
    os.environ['gPDY'] = str(gPDY)
    gdate = os.environ['gPDY']+os.environ['gcyc']
    window_begin = valid_time - dt.timedelta(hours=assim_freq/2)

    config = {
        'valid_time': f"{valid_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'window_begin': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'ATM_WINDOW_BEGIN': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'prev_valid_time': f"{prev_cycle.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'atm_window_length': f"PT{assim_freq}H",
        'ATM_WINDOW_LENGTH': f"PT{assim_freq}H",
        'OBS_DIR': os.environ['COMOUT'],
        'OBS_PREFIX': f"{os.environ['CDUMP']}.t{os.environ['cyc']}z.",
        'target_dir': os.environ['COMOUT'],
        'OBS_DATE': cdate,
        'BIAS_IN_DIR': os.environ['COMOUT'],
        'BIAS_PREFIX': f"{os.environ['GDUMP']}.t{os.environ['gcyc']}z.",
        'BIAS_DATE': gdate,
        'experiment': os.getenv('PSLOT', 'test'),
    }
    config['BKG_YYYYmmddHHMMSS'] = valid_time.strftime('%Y%m%d.%H%M%S')
    config['BKG_ISOTIME'] = valid_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    # some keys we can pull directly from the environment
    env_keys = [
        'CASE', 'CASE_ANL', 'CASE_ENKF', 'DOHYBVAR', 'LEVS', 'OBS_YAML_DIR', 'OBS_LIST',
    ]
    for key in env_keys:
        config[key] = os.environ[key]
    config['atm'] = True if component == 'atm' else False
    # compute some other things here
    config['npx_ges'] = int(os.environ['CASE'][1:]) + 1
    config['npy_ges'] = int(os.environ['CASE'][1:]) + 1
    config['npz_ges'] = int(os.environ['LEVS']) - 1
    config['npx_anl'] = int(os.environ['CASE_ANL'][1:]) + 1
    config['npy_anl'] = int(os.environ['CASE_ANL'][1:]) + 1
    config['npz_anl'] = int(os.environ['LEVS']) - 1

    return config
