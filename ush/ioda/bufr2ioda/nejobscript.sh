#!/bin/bash -l
#
# -- Request that this job run on orion
#SBATCH --partition=orion
#
# -- Request 20 cores
#SBATCH --ntasks=20
#
# -- Specify a maximum wallclock of 4 hours
#SBATCH --time=0:30:00
#
# -- Specify under which account a job should run
#SBATCH --account=da
#
# -- Set the name of the job, or Slurm will default to the name of the script
#SBATCH --job-name=NEacft
#
# -- Tell the batch system to set the working directory to the current working directory
#SBATCH --chdir=.

nt=20 #$SLURM_NTASKS

module use /work2/noaa/da/nesposito/GDASApp_20231012/modulefiles
module load GDAS/orion
module unload bufr
export bufr_ROOT=/work2/noaa/da/nesposito/nceplibs_bufr_readlc_20231012/build/bufr
export bufrlib_ROOT=/work2/noaa/da/nesposito/nceplibs_bufr_readlc_20231012/build/bufr
PYIODALIB=`echo /work2/noaa/da/nesposito/GDASApp_20231012/build/lib/python3.7`
export PYTHONPATH=${PYIODALIB}:${PYTHONPATH}

srun -n $nt --nodes=4  python run_bufr2ioda.py 2021080100 gdas /work/noaa/rstprod/dump/ /work2/noaa/da/nesposito/GDASApp_20231012/parm/ioda/bufr2ioda/ /work2/noaa/da/nesposito/NewConv/api_convert/json/json_gdasapp 
