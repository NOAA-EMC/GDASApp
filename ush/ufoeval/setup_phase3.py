#!/usr/bin/env python3
import yaml
import os
import shutil
import subprocess
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                    level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

jobname = "runjob"


class SlurmJobCard:

    def __init__(self, config):
        """
        Constructor for the SlurmJobCard class.
        :param config: dictionary containing configuration information
        """

        self.config = config

        self.appcore = config['app files']['DA_CORE']
        self.apptype = config['app files']['DA_TYPE']
        self.appexe = config['app files']['APPEXE']

        self.machine = config['machine']
        self.homegfs = config['directories']['HOMEgfs']
        self.rundir = os.path.join(config['directories']['RUNDIR'], self.appcore + '_' + self.apptype)
        if self.appcore == 'jedi':
            self.incexe = config['app files']['INCEXE']
        self.nodes = config['job options']['nodes']
        self.ppn = config['job options']['tasks-per-node']
        self.ntasks = self.nodes * self.ppn
        self.threads = config['job options']['cpus-per-task']

        self.f = open(jobname + ".sh", "w")
        self.f.write("#!/usr/bin/env bash\n")
        self.f.write(f"# Running on {self.machine} \n")

    def header(self):
        """
        Write machine dependent scheduler header
        TODO: generalize to support more than just slurm
        """
        self.f.write(f"#SBATCH --output={jobname}.o%J\n")

        sbatch = ''
        for key, value in self.config['job options'].items():
            sbatch += f"#SBATCH --{key}={value} \n"

        self.f.write(f"{sbatch}\n")

    def load_modules(self):
        """
        Load modules
        """
        self.f.write("\n")
        self.f.write("# Load modules\n")
        self.f.write(f"export HOMEgfs={self.homegfs}\n")
        self.f.write(f"source {self.homegfs}/ush/preamble.sh\n")
        if self.appcore == 'gsi':
            self.f.write(f". {self.homegfs}/ush/load_fv3gfs_modules.sh\n")
        else:
            self.f.write(f". {self.homegfs}/ush/load_ufsda_modules.sh\n")
        self.f.write("set -x\n")

    def aprun(self):
        """
        Execute app
        """

        # cd to run directory
        self.f.write("\n")
        self.f.write(f"# cd to run directory\n")
        self.f.write(f"cd {self.rundir}\n")

        # copy or link app executable
        self.f.write("\n")
        if self.appcore == 'gsi':
            self.f.write(f"# Copy executable\n")
            self.f.write(f"cp -p {self.appexe} ./gsi.x\n")
        else:
            self.f.write(f"# Link executables\n")
            self.f.write(f"ln -fs {self.appexe} ./gdas.x\n")
            self.f.write(f"ln -fs {self.incexe} ./fv3jedi_fv3inc.x\n")

        # execute app
        self.f.write("\n")
        self.f.write(f"# Execute app\n")
        self.f.write(f"export OMP_NUM_THREADS={self.threads}\n")
        self.f.write(f"ulimit -s unlimited\n")

        if self.appcore == 'gsi':
            aprun_command = f"srun -n {self.ntasks} --cpus-per-task={self.threads} ./gsi.x"
        else:
            aprun_command = f"srun -n {self.ntasks} --cpus-per-task={self.threads} ./gdas.x fv3jedi variational ./atmanlvar.yaml"

        self.f.write(f"{aprun_command}\n")

        # JEDI jobs convert cube sphere increments to gausssian grid for comparison
        if self.appcore == 'jedi':
            if self.apptype != "hyb4denv":
                self.f.write("\n")
                self.f.write(f"# Convert cube sphere increments to gaussian grid\n")
                aprun_command = f"srun -n {self.ntasks} --cpus-per-task={self.threads} ./fv3jedi_fv3inc.x ./atmanlfv3inc.yaml"
                self.f.write(f"{aprun_command}\n")
            else:
                # JEDI hyb4denv jobs convert cube sphere increments to gaussian for multiple analysis times
                self.f.write("\n")
                self.f.write(f"# Convert cube sphere increments to gaussian grid\n")
                aprun_command = f"srun -n {self.ntasks} --cpus-per-task={self.threads} ./fv3jedi_fv3inc.x ./atmanlfv3inc03.yaml"
                self.f.write(f"{aprun_command}\n")
                aprun_command = f"srun -n {self.ntasks} --cpus-per-task={self.threads} ./fv3jedi_fv3inc.x ./atmanlfv3inc06.yaml"
                self.f.write(f"{aprun_command}\n")
                aprun_command = f"srun -n {self.ntasks} --cpus-per-task={self.threads} ./fv3jedi_fv3inc.x ./atmanlfv3inc09.yaml"
                self.f.write(f"{aprun_command}\n")

    def close(self):
        """
        Flush and make the card executable
        """
        self.f.close()
        subprocess.run(["chmod", "+x", jobname + ".sh"])


def main():
    epilog = ["Examples:",
              "   ./run.py -c config.yaml",
              "   ./run.py -h"]
    parser = argparse.ArgumentParser(description="Set up atmospheric DA run.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=os.linesep.join(epilog))
    parser.add_argument("-c", "--config", required=True, help="The YAML file")
    args = parser.parse_args()

    # Get the experiment configuration
    run_jjobs_yaml = args.config
    with open(run_jjobs_yaml, 'r') as file:
        exp_config = yaml.safe_load(file)

    logging.info(f"exp_config {exp_config}")

    # Set DA core and type
    appcore = exp_config['app files']['DA_CORE']
    apptype = exp_config['app files']['DA_TYPE']

    # Ensure valid app core and type
    valid = ['gsi', 'jedi']
    if appcore not in valid:
        raise ValueError(f"DA_CORE {appcore} is invalid.  Valid cores are {valid}")

    valid = ['3dv', '3dvfgat', 'hyb3dvfgat', 'hyb4denv']
    if apptype not in valid:
        raise ValueError(f"DA_TYPE {apptype} is invalid.  Valid types are {valid}")

    # Set source (stagedir) and destination (rundir) paths
    stagedir = os.path.join(exp_config['directories']['STAGEDIR'], appcore, apptype)
    rundir = os.path.join(exp_config['directories']['RUNDIR'], appcore + '_' + apptype)

    # Create and cd to run directory
    if os.path.exists(rundir):
        shutil.rmtree(rundir)
    os.makedirs(rundir)
    os.chdir(rundir)
    if appcore == 'jedi':
        os.makedirs(f"{rundir}/anl")
        os.makedirs(f"{rundir}/diags")

    # Copy files and directories to run directory
    if appcore == 'gsi':
        files_to_copy = [
            "*info*", "aircftbias_in", "atms_beamwidth.txt", "berror_stats",
            "cloudy_radiance_info.txt", "errtable", "gsiparm.anl", "prepbufr", "radstat.gdas",
            "AIRS_CLDDET.NL", "CRIS_CLDDET.NL", "IASI_CLDDET.NL", "Rcov*", "satbias_angle",
            "satbias_in", "satbias_pc", "sfcf*", "sigf*", "vqctp001.dat"
        ]
        for pattern in files_to_copy:
            for file_path in Path(stagedir).glob(pattern):
                shutil.copy(file_path, rundir)

        directories_to_copy = ["crtm_coeffs", "ensemble_data"]
        for directory in directories_to_copy:
            source_dir = Path(stagedir) / directory
            if source_dir.exists():
                shutil.copytree(source_dir, Path(rundir) / directory)

    else:
        # Copy files and directories to run directory
        files_to_copy = [
            "atmanlvar.yaml", "atmanlfv3inc*.yaml"
        ]
        for pattern in files_to_copy:
            for file_path in Path(stagedir).glob(pattern):
                shutil.copy(file_path, rundir)

        directories_to_copy = ["berror", "bkg", "crtm", "ens", "fv3jedi", "obs"]
        for directory in directories_to_copy:
            source_dir = Path(stagedir) / directory
            if source_dir.exists():
                shutil.copytree(source_dir, Path(rundir) / directory)

    logging.info(f"Data staged to {rundir}")

    # Create run script
    run_card = SlurmJobCard(exp_config)
    run_card.header()
    run_card.load_modules()
    run_card.aprun()
    run_card.close()

    logging.info(f"Create {jobname}.sh in {rundir}")


if __name__ == "__main__":
    main()
