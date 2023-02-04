#!/usr/bin/env python3
import yaml
import os
import sys
import subprocess
import argparse


machines = {"container", "hera", "orion"}
MODS = {'JGDAS_GLOBAL_OCEAN_ANALYSIS_PREP': 'GDAS',
        'JGDAS_GLOBAL_OCEAN_ANALYSIS_BMAT': 'GDAS',
        'JGDAS_GLOBAL_OCEAN_ANALYSIS_RUN': 'GDAS',
        'JGDAS_GLOBAL_OCEAN_ANALYSIS_POST': 'GDAS',
        'JGDAS_GLOBAL_OCEAN_ANALYSIS_VRFY': 'EVA'}
components_short = {'ocean': 'ocn', 'ice': 'ice'}


class JobCard:

    def __init__(self, scriptname, config):
        """
        Constructor for the JobCard class.
        :param scriptname: name of the script file
        :param config: dictionary containing configuration information
        """
        self.name = scriptname
        self.f = open(self.name, "w")
        self.f.write("#!/usr/bin/env bash\n")
        self.component = config['gw environement']['experiment identifier']['COMPONENT']
        self.pslot = config['gw environement']['experiment identifier']['PSLOT']
        self.homegfs = config['gw environement']['experiment identifier']['HOMEgfs']
        self.stmp = config['gw environement']['working directories']['STMP']
        self.rotdirs = config['gw environement']['working directories']['ROTDIR']
        self.expdirs = config['gw environement']['working directories']['EXPDIRS']
        self.config = config
        self.machine = config['machine']

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
        DATAROOT = os.path.join(config['working directories']['STMP'], 'RUNDIRS', self.pslot)
        gcyc = str((config['cycle info']['cyc'] - config['cycle info']['assym_freq']) % 24).zfill(2)
        CDATE = f"{config['cycle info']['PDY']}{config['cycle info']['cyc']}"  # TODO: Not needed after Andy's PR

        # Write the export commands for the remaining environment variables
        self.f.write(f"export EXPDIR='{EXPDIR}'\n")
        self.f.write(f"export DATAROOT='{DATAROOT}'\n")
        self.f.write(f"export gcyc='{gcyc}'\n")
        self.f.write(f"export CDATE='{CDATE}'\n")

        # Add to python environement
        self.f.write("PYTHONPATH=${HOMEgfs}/ush/python/pygw/src:${PYTHONPATH}\n")

    def setupexpt(self):
        """
        Write a call to the global-worflow utility setup_expt.py
        """

        # Make a copy of the configs
        origconfig = "${HOMEgfs}/parm/config"
        self.f.write("\n")
        self.f.write("# Make a copy of config\n")
        self.f.write(f"cp -r {origconfig} .\n")

        # Dump the configs in a separate yaml file
        with open("overwrite_defaults.yaml", "w") as f:
            yaml.safe_dump(self.config['setup_expt config'], f)

        # Setup the experiment
        self.f.write("\n")
        self.f.write("# Setup the experiment\n")

        setupexpt = "${HOMEgfs}/workflow/setup_expt.py cycled "
        # Most of the args keys are not used to run the jjobs but are needed to run setup_expt.py
        args = {
            "idate": "${PDY}${cyc}",
            "edate": "${PDY}${cyc}",
            "app": "ATM",
            "start": "warm",
            "gfs_cyc": "0",
            "resdet": self.config['resdet'],
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
        self.f.write(f"{setupexpt}\n")

    def close(self):
        """
        Flush and make the card executable
        """
        self.f.close()
        subprocess.run(["chmod", "+x", self.name])

    def _modules(self, jjob):
        """
        Write a section that will load the machine dependent modules
        """
        if self.machine != "container":
            self.f.write("module purge \n")
            self.f.write("module use ${HOMEgfs}/sorc/gdas.cd/modulefiles \n")
            self.f.write(f"module load {MODS[jjob]}/{self.machine} \n")

    def copy_bkgs(self):
        """
        Fill the ROTDIR with backgrounds
        TODO: replace by fill comrot?
        """
        file_descriptor = components_short[self.component]+'f0'
        self.f.write("mkdir -p ${ROTDIR}/${PSLOT}/gdas.${PDY}/${gcyc}/${COMPONENT}/\n")
        command = "cp -r ${COMIN_GES}/*." + file_descriptor + "*.nc"
        command += "  ${ROTDIR}/${PSLOT}/gdas.${PDY}/${gcyc}/${COMPONENT}/\n"
        self.f.write(command)
        # Special case for the ocean: DA for ice & ocean
        if self.component == 'ocean':
            # staging seaice backgrounds
            ice_file_descriptor = components_short['ice']
            self.f.write("mkdir -p ${ROTDIR}/${PSLOT}/gdas.${PDY}/${gcyc}/ice/\n")
            self.f.write("cp -r ${COMIN_GES}/*icef0*.nc ${ROTDIR}/${PSLOT}/gdas.${PDY}/${gcyc}/ice/\n")

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
        var2replace = {'HOMEgfs': self.homegfs,
                       'STMP': self.stmp,
                       'ROTDIRS': self.rotdirs,
                       'EXPDIRS': self.expdirs}
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
            self._modules(job)  # Add module's jjob
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
    epilog = ["Make sure the comrot, experiment and config directories are removed before running this script",
              "Examples:",
              "   ./run_jjobs.py -y run_jjobs_orion.yaml",
              "   ./run_jjobs.py -h"]
    parser = argparse.ArgumentParser(description="Run an ordered list of j-jobs.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=os.linesep.join(epilog))
    parser.add_argument("-y", "--yaml", required=True, help="The YAML file")
    parser.add_argument("-s", "--skip", action='store_true', default=False, help="Skip setup_expt.sh if present")
    args = parser.parse_args()

    # Get the experiment configuration
    run_jjobs_yaml = args.yaml
    with open(run_jjobs_yaml, 'r') as file:
        exp_config = yaml.safe_load(file)

    if not args.skip:
        # Write a setup card (prepare COMROT, configs, ...)
        setup_card = JobCard("setup_expt.sh", exp_config)
        setup_card.export_env_vars_script()
        setup_card.setupexpt()
        setup_card.close()     # flush to file, close and make it executable
        setup_card.execute()   # run the setup card

    # Write the j-jobs card
    run_card = JobCard("run_jjobs.sh", exp_config)
    run_card.fixconfigs()                # over-write some of the config variables
    run_card.header()                    # prepare a machine dependent header (SLURM or nothing)
    run_card.export_env_vars_script()
    run_card.copy_bkgs()
    run_card.jjobs()
    run_card.close()

    # Submit/Run the j-jobs card
    run_card.execute(submit=True)


if __name__ == "__main__":
    main()
