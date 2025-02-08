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


class JobCard:

    def __init__(self, scriptname, config):
        """
        Constructor for the JobCard class.
        :param scriptname: name of the output script file
        :param config: dictionary containing configuration information
        """

        self.name = scriptname
        self.config = config

        self.machine = config['machine']
        self.homegfs = config['directories']['HOMEgfs']
        self.rundir = config['directories']['RUNDIR']
        self.appexe = config['app files']['APPEXE']
        self.appyml = config['app files']['APPYML']
        self.jobname = config['job options']['job-name']
        self.nodes = config['job options']['nodes']
        self.ppn = config['job options']['tasks-per-node']
        self.ntasks = self.nodes * self.ppn
        self.threads = config['job options']['cpus-per-task']

        self.f = open(self.name, "w")
        self.f.write("#!/usr/bin/env bash\n")
        self.f.write(f"# Running on {self.machine} \n")

    def header(self):
        """
        Write machine dependent scheduler header
        TODO: generalize to support more than just slurm
        """
        self.f.write(f"#SBATCH --output={self.jobname}.o%J\n")

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
        self.f.write(f". {self.homegfs}/ush/load_fv3gfs_modules.sh\n")
        self.f.write("set -x\n")

    def aprun(self):
        """
        Execute app
        """

        # cd to run directory
        self.f.write("\n")
        self.f.write(f"# cd to run directory\n")
        self.f.write(f"cd {self.rundir}\n")

        # copy app files
        self.f.write("\n")
        self.f.write(f"# Copy executable and namelist\n")
        self.f.write(f"cp -p {self.appexe} ./app.x\n")
        self.f.write(f"cp -p {self.appyml} ./\n")

        # execute app
        self.f.write("\n")
        self.f.write(f"# Execute app\n")
        self.f.write(f"export OMP_NUM_THREADS={self.threads}\n")
        self.f.write(f"ulimit -s unlimited\n")

        aprun_command = f"srun -n {self.ntasks} --cpus-per-task={self.threads} ./app.x"
        self.f.write(f"{aprun_command}\n")

    def close(self):
        """
        Flush and make the card executable
        """
        self.f.close()
        subprocess.run(["chmod", "+x", self.name])


def main():
    epilog = ["Examples:",
              "   ./run_jjobs.py -y config.yaml",
              "   ./run_jjobs.py -h"]
    parser = argparse.ArgumentParser(description="Run an ordered list of j-jobs.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=os.linesep.join(epilog))
    parser.add_argument("-y", "--yaml", required=True, help="The YAML file")
    args = parser.parse_args()

    # Get the experiment configuration
    run_jjobs_yaml = args.yaml
    with open(run_jjobs_yaml, 'r') as file:
        exp_config = yaml.safe_load(file)

    logging.info(f"exp_config {exp_config}")

    # Set source (stagedir) and destination (rundir) paths
    stagedir = exp_config['directories']['STAGEDIR']
    rundir = exp_config['directories']['RUNDIR']

    # Create and cd to run directory
    if os.path.exists(rundir):
        shutil.rmtree(rundir)
    os.makedirs(rundir)
    os.chdir(rundir)

    # Copy files and directories to run directory
    files_to_copy = [
        "*info*", "aircftbias_in", "atms_beamwidth.txt", "berror_stats",
        "cloudy_radiance_info.txt", "errtable", "prepbufr", "radstat.gdas", "AIRS_CLDDET.NL",
        "CRIS_CLDDET.NL", "IASI_CLDDET.NL", "Rcov*", "satbias_angle", "satbias_in",
        "satbias_pc", "sfcf06", "sigf06", "vqctp001.dat"
    ]
    for pattern in files_to_copy:
        for file_path in Path(stagedir).glob(pattern):
            shutil.copy(file_path, rundir)

    directories_to_copy = ["crtm_coeffs"]
    for directory in directories_to_copy:
        source_dir = Path(stagedir) / directory
        if source_dir.exists():
            shutil.copytree(source_dir, Path(rundir) / directory)

    logging.info(f"Data staged to {rundir}")

    # Create run script.
    runscript = exp_config['app files']['runscript']
    run_card = JobCard(runscript, exp_config)
    run_card.header()
    run_card.load_modules()
    run_card.aprun()
    run_card.close()

    logging.info(f"Create {runscript} in {rundir}")


if __name__ == "__main__":
    main()
