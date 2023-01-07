#!/usr/bin/env python3
import yaml
import os
import sys
import re
import subprocess


def execute_script(script):
    # Execute prep.sh
    try:
        subprocess.check_output(["bash", script])
    except subprocess.CalledProcessError as e:
        print(f"{script} failed with return code:", e.returncode)


def export_env_vars_script(config, bash_script, pslot):
    # export the variables in config
    bash_script.write("\n")
    bash_script.write("# Export jjob environement\n")
    for key, value in config.items():
        for subkey, subvalue in value.items():
            bash_script.write(f"export {subkey}='{subvalue}'\n")

    # Compute remaining environment variables
    EXPDIR = os.path.join(config['working directories']['EXPDIRS'], pslot)
    DATAROOT = os.path.join(config['working directories']['STMP'], 'RUNDIRS', pslot)
    gcyc = str((config['cycle info']['cyc'] - config['cycle info']['assym_freq']) % 24).zfill(2)
    CDATE = f"{config['cycle info']['PDY']}{config['cycle info']['cyc']}"  # TODO: Not needed after Andy's PR

    # Write the export commands for the remaining environment variables
    bash_script.write(f"export EXPDIR='{EXPDIR}'\n")
    bash_script.write(f"export DATAROOT='{DATAROOT}'\n")
    bash_script.write(f"export gcyc='{gcyc}'\n")
    bash_script.write(f"export CDATE='{CDATE}'\n")

    # Add to python environement
    # TODO: Should that be in the yaml as pythonpath path "key" listing all the python paths
    #       needed to run the jjobs?
    bash_script.write("PYTHONPATH=${HOMEgfs}/ush/python/pygw/src:${PYTHONPATH}\n")


def slurm_header(config, script):
    sbatch = ''
    for key, value in config.items():
        print(key)
        sbatch += f"#SBATCH --{key} {value} \n"
    script.write(f"{sbatch}\n")


# Get the experiment configuration
with open("run_jjobs.yaml", "r") as file:
    exp_config = yaml.safe_load(file)

# define variables of convenience
pslot = exp_config['gw environement']['experiment identifier']['PSLOT']
homegfs = exp_config['gw environement']['experiment identifier']['HOMEgfs']
stmp = exp_config['gw environement']['working directories']['STMP']
rotdirs = exp_config['gw environement']['working directories']['ROTDIR']
expdirs = exp_config['gw environement']['working directories']['EXPDIRS']

# Generate the setup_expt.sh script
with open("setup_expt.sh", "w") as bash_script:
    bash_script.write("#!/usr/bin/env bash\n")
    export_env_vars_script(exp_config['gw environement'], bash_script, pslot)

    # Make a copy of the configs
    origconfig = "${HOMEgfs}/parm/config"
    bash_script.write("\n")
    bash_script.write("# Make a copy of config\n")
    bash_script.write(f"cp -r {origconfig} .\n")

    # Dump the configs in a separate yaml file
    with open("overwrite_defaults.yaml", "w") as f:
        yaml.safe_dump(exp_config['configs'], f)

    # Setup the experiment
    bash_script.write("\n")
    bash_script.write("# Setup the experiment\n")

    setupexpt = "${HOMEgfs}/workflow/setup_expt.py cycled "
    # Most of the args keys are not used to run the jjobs but needed to run setupexpt
    args = {
        "idate": "${PDY}${cyc}",
        "edate": "${PDY}${cyc}",
        "app": "ATM",
        "start": "warm",
        "gfs_cyc": "4",
        "resdet": "48",
        "resens": "24",
        "nens": "0",
        "pslot": "${PSLOT}",
        "configdir": "${PWD}/config",
        "comrot": "${ROTDIR}",
        "expdir": "${EXPDIRS}",
        "yaml": "overwrite_defaults.yaml"}

    # Write the arguments of setup_expt.py
    for key, value in args.items():
        setupexpt += f" --{key} {value}"
    bash_script.write(f"{setupexpt}\n")
    bash_script.close()

# Execute prep.sh
execute_script('setup_expt.sh')


# get the machine value ... Do we still need it?
machine = exp_config['machine']

configbase = os.path.join(exp_config['gw environement']['working directories']['EXPDIRS'],
                          exp_config['gw environement']['experiment identifier']['PSLOT'],
                          'config.base')

# Append SLURM directive so the script can be "sbatch'ed"
machines = {"CONTAINER", "HERA"}
if machine in machines:
    print(f'machine is {machine}')
else:
    print(f"Probably does not work for {machine} yet")

# swap a few variables in config.base
var2replace = {'HOMEgfs': homegfs, 'STMP': stmp, 'ROTDIRS': rotdirs, 'EXPDIRS': expdirs}
with open(configbase, 'r') as f:
    newconfigbase = f.read()
for key, value in var2replace.items():
    newconfigbase = newconfigbase.replace(f'{key}=', f'{key}={value} #')
with open(configbase, 'w') as f:
    f.write(newconfigbase)

# Generate the script that runs the jjobs
with open("run_jjobs.sh", "w") as bash_script:
    # TODO: Add SLURM directive to the header of the script
    bash_script.write("#!/usr/bin/env bash\n")
    sbatch = './'
    if machine != "CONTAINER":
        slurm_header(exp_config['job options'], bash_script)
        sbatch = 'sbatch '

    export_env_vars_script(exp_config['gw environement'], bash_script, pslot)

    # Copy backgrounds from previous cycle
    bash_script.write("mkdir -p ${ROTDIR}/${PSLOT}/gdas.${PDY}/${gcyc}/${COMPONENT}/\n")
    bash_script.write("cp -r ${COMIN_GES}/* ${ROTDIR}/${PSLOT}/gdas.${PDY}/${gcyc}/${COMPONENT}/\n")

    runjobs = "# Run jjobs\n"
    for job in exp_config['jjobs']:
        thejob = "${HOMEgfs}/jobs/"+job
        runjobs += f"{thejob} &>{job}.out\n"
    bash_script.write(runjobs)


execute_script(sbatch+'run_jjobs.sh')
