#!/usr/bin/env python3
import yaml
import os
import sys
import subprocess
import argparse
from datetime import datetime, timedelta

machines = {"container", "hera", "orion", "hercules", "wcoss2"}

# Assume the default conda environement is gdassapp
ENVS = {'JGDAS_GLOBAL_OCEAN_ANALYSIS_VRFY': 'eva'}
components_short = {'ocean': 'ocn', 'ice': 'ice'}  # Short names for components


class JobCard:

    def __init__(self, scriptname, config, ctest=False):
        """
        Constructor for the JobCard class.
        :param scriptname: name of the script file
        :param config: dictionary containing configuration information
        """
        self.name = scriptname
        self.config = config
        self.machine = config['machine']
        self.f = open(self.name, "w")
        self.f.write("#!/usr/bin/env bash\n")
        self.f.write(f"# Running on {self.machine} \n")

        # Exit early if not testing a gw jjob
        print(config)
        if ctest:
            self.header()
            # Hard coded to one task for now
            mpiexec = "mpirun -np 1"
            if self.machine != "container":
                mpiexec = "srun -n 1"
            command = f"{mpiexec} {config['ctest command']['executable']} {config['ctest command']['yaml input']}"
            self.f.write(f"{command} \n")
            return

        self.pslot = config['gw environement']['experiment identifier']['PSLOT']
        self.homegfs = config['gw environement']['experiment identifier']['HOMEgfs']
        self.stmp = config['gw environement']['working directories']['STMP']
        self.rotdirs = config['gw environement']['working directories']['ROTDIRS']
        self.rotdir = os.path.join(self.rotdirs, self.pslot)
        self.expdirs = config['gw environement']['working directories']['EXPDIRS']

        # get cycle info
        self.PDY = config['gw environement']['cycle info']['PDY']
        self.cyc = config['gw environement']['cycle info']['cyc']
        self.assim_freq = config['gw environement']['cycle info']['assym_freq']
        self.RUN = config['gw environement']['experiment identifier']['RUN']

        # compute previous cycle info
        gdate = datetime.strptime(f"{self.PDY}{self.cyc}", '%Y%m%d%H') - timedelta(hours=self.assim_freq)
        self.gPDY = gdate.strftime("%Y%m%d")
        self.gcyc = gdate.strftime("%H")
        self.com_src = config['gw environement']['backgrounds']['COM_SRC']

    def header(self):
        """
        Write machine dependent scheduler header
        """
        if self.machine != "container":
            sbatch = ''
            for key, value in self.config['job options'].items():
                sbatch += f"#SBATCH --{key}={value} \n"
            self.f.write(f"{sbatch}\n")

    def export_env_vars_script(self):
        """
        Write the exports needed by the global-workflow environement
        """
        self.f.write("\n")
        self.f.write("# Export jjob environement\n")
        for key, value in self.config['gw environement'].items():
            for subkey, subvalue in value.items():
                self.f.write(f"export {subkey}='{subvalue}'\n")

        # Compute remaining environment variables
        config = self.config['gw environement']
        EXPDIR = os.path.join(config['working directories']['EXPDIRS'], self.pslot)
        ROTDIR = self.rotdir
        DATAROOT = os.path.join(config['working directories']['STMP'], 'RUNDIRS', self.pslot)
        gcyc = str((config['cycle info']['cyc'] - config['cycle info']['assym_freq']) % 24).zfill(2)
        CDATE = f"{config['cycle info']['PDY']}{config['cycle info']['cyc']}"  # TODO: Not needed after Andy's PR

        # Write the export commands for the remaining environment variables
        self.f.write(f"export EXPDIR='{EXPDIR}'\n")
        self.f.write(f"export ROTDIR='{ROTDIR}'\n")
        self.f.write(f"export DATAROOT='{DATAROOT}'\n")
        self.f.write(f"export gcyc='{gcyc}'\n")
        self.f.write(f"export CDATE='{CDATE}'\n")

        # Add to python environment
        self.f.write("PYTHONPATH=${HOMEgfs}/ush/python:${PYTHONPATH}\n")

    def setupexpt(self):
        """
        Write a call to the global-worflow utility setup_expt.py
        """

        # Make a copy of the configs
        origconfig = "${HOMEgfs}/parm/config/gfs"
        self.f.write("\n")
        self.f.write("# Make a copy of config\n")
        self.f.write(f"mkdir -p config\n")
        self.f.write(f"cp -r {origconfig} config/\n")

        # Dump the configs in a separate yaml file
        with open("overwrite_defaults.yaml", "w") as f:
            yaml.safe_dump(self.config['setup_expt config'], f)

        # Setup the experiment
        self.f.write("\n")
        self.f.write("# Setup the experiment\n")

        setupexpt = "${HOMEgfs}/workflow/setup_expt.py gfs cycled "
        # Most of the args keys are not used to run the jjobs but are needed to run setup_expt.py
        args = {
            "idate": "${PDY}${cyc}",
            "edate": "${PDY}${cyc}",
            "app": "ATM",
            "start": "warm",
            "gfs_cyc": "0",
            "resdetatmos": self.config['resdetatmos'],
            "resensatmos": self.config['resensatmos'],
            "nens": "0",
            "pslot": "${PSLOT}",
            "configdir": "${PWD}/config/gfs",
            "comroot": self.rotdir,
            "expdir": "${EXPDIRS}",
            "yaml": "overwrite_defaults.yaml"}

        # Write the arguments of setup_expt.py
        for key, value in args.items():
            setupexpt += f" --{key} {value}"
        self.f.write(f"{setupexpt}\n")

    def close(self):
        """
        Flush and make the card executable
        """
        self.f.close()
        subprocess.run(["chmod", "+x", self.name])

    def _conda_envs(self, jjob):
        """
        Write a section that will load the machine dependent modules
        """
        if self.machine in ["orion", "hercules"]:
            if jjob in ENVS:
                # set +/-u is a workaround for an apparent conda bug
                self.f.write(f"set +u \n")
                self.f.write(f"conda activate {ENVS[jjob]} \n")
                self.f.write(f"set -u \n")
        elif self.machine in ["hera", "wcoss2"]:
            if jjob in ENVS:
                self.f.write(f"module load {ENVS[jjob].upper()}/{self.machine} \n")

    def precom(self, com, tmpl):
        cmd = f"RUN={self.RUN} YMD={self.gPDY} HH={self.gcyc} declare_from_tmpl -xr {com}:{tmpl}"
        self.f.write(f"{cmd}\n")

    def copy_bkgs(self):
        """
        Fill the ROTDIR with backgrounds
        TODO: replace by fill comroot?
        """
        print(f"gPDY: {self.gPDY}")
        print(f"gcyc: {self.gcyc}")
        print(f"assim_freq: {self.assim_freq}")
        print(f"RUN: {self.RUN}")

        # setup COM variables
        self.f.write("source ${HOMEgfs}/parm/config/gfs/config.com\n")
        self.f.write("source ${HOMEgfs}/ush/preamble.sh\n")
        self.precom('COM_OCEAN_HISTORY_PREV', 'COM_OCEAN_HISTORY_TMPL')
        self.precom('COM_ICE_HISTORY_PREV', 'COM_ICE_HISTORY_TMPL')
        self.precom('COM_ICE_RESTART_PREV', 'COM_ICE_RESTART_TMPL')

        self.f.write("mkdir -p ${COM_OCEAN_HISTORY_PREV}/\n")
        self.f.write("mkdir -p ${COM_ICE_HISTORY_PREV}/\n")
        self.f.write("mkdir -p ${COM_ICE_RESTART_PREV}/\n")

        model = os.path.join(self.com_src, f"{self.RUN}.{self.gPDY}", self.gcyc, "model")
        com_ocean_history_src = os.path.join(model, 'ocean', 'history')
        com_ice_history_src = os.path.join(model, 'ice', 'history')
        com_ice_restart_src = os.path.join(model, 'ice', 'restart')
        self.f.write(f"cp {com_ocean_history_src}/*.ocean.*.nc $COM_OCEAN_HISTORY_PREV \n")
        self.f.write(f"cp {com_ice_history_src}/*.ice.*.nc $COM_ICE_HISTORY_PREV \n")
        self.f.write(f"cp {com_ice_restart_src}/*cice_model*.nc $COM_ICE_RESTART_PREV \n")

        # copy ensemble members
        ensbkgs = os.path.join(self.com_src, f"enkf{self.RUN}.{self.gPDY}")
        if os.path.exists(os.path.join(ensbkgs, self.gcyc)):
            self.f.write(f"cp -r {ensbkgs} $ROTDIR \n")
        else:
            print('Aborting, ensemble backgrounds not found')
            sys.exit(1)

    def fixconfigs(self):
        """
        Replace cone of the env. var. in the configs
        """
        configbase = os.path.join(self.config['gw environement']['working directories']['EXPDIRS'],
                                  self.config['gw environement']['experiment identifier']['PSLOT'],
                                  'config.base')

        # Append SLURM directive so the script can be "sbatch'ed"
        if self.machine in machines:
            print(f'machine is {self.machine}')
        else:
            print(f"Probably does not work for {machine} yet")

        # swap a few variables in config.base
        self.homegfs_real = os.path.realpath(self.homegfs)
        var2replace = {'HOMEgfs': self.homegfs_real,
                       'STMP': self.stmp,
                       'ROTDIR': self.rotdir,
                       'EXPDIRS': self.expdirs}

        if 'JGLOBAL_PREP_OCEAN_OBS' in self.config['jjobs']:
            dmpdir = self.config['setup_expt config']['prepoceanobs']['DMPDIR']
            var2replace['DMPDIR'] = dmpdir

        with open(configbase, 'r') as f:
            newconfigbase = f.read()
        for key, value in var2replace.items():
            newconfigbase = newconfigbase.replace(f'{key}=', f'{key}={value} #')
        with open(configbase, 'w') as f:
            f.write(newconfigbase)

    def jjobs(self):
        """
        Add the list of j-jobs to the job card
        """
        for job in self.config['jjobs']:
            self._conda_envs(job)  # Add module's jjob
            thejob = "${HOMEgfs}/jobs/"+job
            runjob = f"{thejob} &>{job}.out\n"
            self.f.write(runjob)

    def execute(self, submit=False):
        """
        Execute the script
        """
        if not submit or self.machine == "container":
            print(f"running ./{self.name} ...")
            subprocess.check_output([f"./{self.name}"])
            return

        print(f"running sbatch --wait {self.name} ...")
        subprocess.check_output(["sbatch", "--wait", self.name])


def main():
    epilog = ["Make sure the comroot, experiment and config directories are removed before running this script",
              "Examples:",
              "   ./run_jjobs.py -y run_jjobs_orion.yaml",
              "   ./run_jjobs.py -h"]
    parser = argparse.ArgumentParser(description="Run an ordered list of j-jobs.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=os.linesep.join(epilog))
    parser.add_argument("-y", "--yaml", required=True, help="The YAML file")
    parser.add_argument("-s", "--skip", action='store_true', default=False, help="Skip setup_expt.sh if present")
    parser.add_argument("-c", "--ctest", default=False, help="If true, the test is not a jjob (default)")
    args = parser.parse_args()

    # Get the experiment configuration
    run_jjobs_yaml = args.yaml
    with open(run_jjobs_yaml, 'r') as file:
        exp_config = yaml.safe_load(file)

    if not args.skip:
        # Write a setup card (prepare COMROOT, configs, ...)
        setup_card = JobCard("setup_expt.sh", exp_config)
        setup_card.export_env_vars_script()
        setup_card.setupexpt()
        setup_card.close()     # flush to file, close and make it executable
        setup_card.execute()   # run the setup card

    if args.ctest:
        # Write the ctest card
        run_card = JobCard("run_jjobs.sh", exp_config, ctest=True)
    else:
        # Write the j-jobs card
        run_card = JobCard("run_jjobs.sh", exp_config)
        run_card.fixconfigs()                # over-write some of the config variables
        run_card.header()                    # prepare a machine dependent header (SLURM or nothing)
        run_card.export_env_vars_script()
        run_card.copy_bkgs()
        run_card.jjobs()
        run_card.close()

    run_card.close()

    # Submit/Run the j-jobs card
    run_card.execute(submit=True)


if __name__ == "__main__":
    main()
