export GDAS_CI_ROOT=/work2/noaa/da/role-da/CI/hercules/GDASApp
export GDAS_CI_HOST='hercules'
export GDAS_MODULE_USE=$GDAS_CI_ROOT/repo/modulefiles
export SLURM_ACCOUNT=da-cpu
export SALLOC_ACCOUNT=$SLURM_ACCOUNT
export SBATCH_ACCOUNT=$SLURM_ACCOUNT
export SLURM_QOS=debug
export SLURM_EXCLUSIVE=user
export OMP_NUM_THREADS=1
ulimit -s unlimited
export PATH=$PATH:/home/role-da/bin
export NTASKS_TESTS=12
export AUTHORIZED_USERS_FILE=$GDAS_CI_ROOT/authorized_users
