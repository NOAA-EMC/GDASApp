import datetime as dt
import logging
import os
import re
import solo.date
import stat
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
    # also assumes the window is symmetric, probably also bad
    h = int(re.findall('PT(\\d+)H', win_length)[0])
    h2 = int(re.findall('PT(\\d+)H', fcst_step)[0])
    assert h % h2 == 0, "win_length must be divisible by fcst_step"
    if h2 > h//2:
        return [fcst_step]
    start = f'PT{h-h//2}H'
    end = f'PT{h+h//2}H'
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
            f.write(f"export APRUN_SOCAANAL=\"{job_config['mpiexec']} {job_config['mpinproc']} {job_config['ntasks']}\"\n")
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
    valid_time = datetime_from_cdate(os.environ['CDATE'])
    assim_freq = int(os.environ['assim_freq'])
    prev_cycle = valid_time - dt.timedelta(hours=assim_freq)
    window_begin = valid_time - dt.timedelta(hours=assim_freq/2)

    config = {
        'valid_time': f"{valid_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'window_begin': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'prev_valid_time': f"{prev_cycle.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        'atm_window_length': f"PT{assim_freq}H",
        'OBS_DIR': os.environ['COMOUT'],
        'OBS_PREFIX': f"{os.environ['CDUMP']}.t{os.environ['cyc']}z.",
        'target_dir': os.environ['COMOUT'],
        'OBS_DATE': os.environ['CDATE'],
        'BIAS_IN_DIR': os.environ['COMOUT'],
        'BIAS_PREFIX': f"{os.environ['GDUMP']}.t{os.environ['gcyc']}z.",
        'BIAS_DATE': f"{os.environ['GDATE']}",
        'experiment': os.getenv('PSLOT', 'test'),
    }
    # some keys we can pull directly from the environment
    env_keys = [
        'CASE', 'CASE_ANL', 'CASE_ENKF', 'DOHYBVAR', 'LEVS', 'OBS_YAML_DIR', 'OBS_LIST',
    ]
    for key in env_keys:
        config[key] = os.environ[key]
    config['atm'] = True if component == 'atm' else False
    return config
