#!/usr/bin/env python3

import os
import yaml
import sys


def create_job_script(job_config, machine_config):
    scheduler = machine_config.get('SCHEDULER', 'slurm')
    account = machine_config.get('HPC_ACCOUNT')
    queue = machine_config.get('QUEUE')
    partition = machine_config.get('PARTITION_BATCH', 'none')
    cluster = machine_config.get('CLUSTERS', 'none')
    machine_id = machine_config.get('MACHINE_ID', 'none')
    job_name = job_config.get('job_name', 'myjob')
    walltime = job_config.get('walltime', '01:00:00')
    nodes = job_config.get('nodes', 1)
    ntasks_per_node = job_config.get('ntasks_per_node', 1)
    threads_per_task = job_config.get('threads_per_task', 1)
    ncpus = ntasks_per_node * threads_per_task
    memory = job_config.get('memory', '4gb')
    command = job_config.get('command', 'python script.py')
    filename = job_config.get('filename', 'job_script.sh')

    if scheduler == 'pbspro':
        script = f"""#!/bin/bash
#PBS -N {job_name}
#PBS -j oe
#PBS -A {account}
#PBS -q {queue}
#PBS -l walltime={walltime}
#PBS -l select={nodes}:mpiprocs={ntasks_per_node}:ompthreads={threads_per_task}:ncpus={ncpus}:mem={memory}
#PBS -l place=vscatter

set -x
cd $PBS_O_WORKDIR
{command}
"""
    elif scheduler == 'slurm':
        if machine_id == 'gaeac6':
            script = f"""#!/bin/bash
#SBATCH -J {job_name}
#SBATCH -o {job_name}.o%J
#SBATCH -e {job_name}.o%J
#SBATCH -A {account}
#SBATCH -q {queue}
#SBATCH -p {partition}
#SBATCH -M {cluster}
#SBATCH -t {walltime}
#SBATCH --nodes={nodes}
#SBATCH --ntasks-per-node={ntasks_per_node}
#SBATCH --cpus-per-task={threads_per_task}
#SBATCH --mem={memory}

set -x
cd $SLURM_SUBMIT_DIR
{command}
"""
        else:
            script = f"""#!/bin/bash
#SBATCH -J {job_name}
#SBATCH -o {job_name}.o%J
#SBATCH -e {job_name}.o%J
#SBATCH -A {account}
#SBATCH -q {queue}
#SBATCH -p {partition}
#SBATCH -t {walltime}
#SBATCH --nodes={nodes}
#SBATCH --ntasks-per-node={ntasks_per_node}
#SBATCH --cpus-per-task={threads_per_task}
#SBATCH --mem={memory}

set -x
cd $SLURM_SUBMIT_DIR
{command}
"""
    else:
        raise ValueError("Unsupported scheduler. Use 'pbspro' or 'slurm'.")

    with open(filename, 'w') as f:
        f.write(script)

    os.chmod(filename, 0o755)
    print(f"{scheduler.upper()} job script written to {filename}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_job_script.py config.yaml")
        sys.exit(1)

    job_config_file = sys.argv[1]
    with open(job_config_file, 'r') as f:
        job_config = yaml.safe_load(f)

    homegdas = job_config.get('homegdas')
    machine = job_config.get('machine')

    machine_config_file = os.path.join(homegdas, "test/workflow/hosts", machine.lower() + ".yaml")

    with open(machine_config_file, 'r') as f:
        machine_config = yaml.safe_load(f)

    machine_config["MACHINE_ID"] = machine.lower()
    print(f"machine_config {machine_config}")

    create_job_script(job_config, machine_config)


if __name__ == "__main__":
    main()
