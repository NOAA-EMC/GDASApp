help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

prepend_path("MODULEPATH", '/work/noaa/epic/role-epic/spack-stack/orion/spack-stack-1.5.1/envs/unified-env/install/modulefiles/Core')
prepend_path("MODULEPATH", '/work2/noaa/da/python/opt/modulefiles/stack')

-- below two lines get us access to the spack-stack modules
load("stack-gcc/10.2.0")
load("stack-openmpi/4.0.4")
load("stack-python/3.10.8")
load("jedi-fv3-env")
load("soca-env")
load("mkl/2020.2")

setenv("CC","mpiicc")
setenv("FC","mpiifort")
setenv("CXX","mpiicpc")
local mpiexec = '/opt/slurm/bin/srun'
local mpinproc = '-n'
setenv('MPIEXEC_EXEC', mpiexec)
setenv('MPIEXEC_NPROC', mpinproc)

setenv("CRTM_FIX","/work2/noaa/da/cmartin/GDASApp/fix/crtm/2.4.0")
setenv("GDASAPP_TESTDATA","/work2/noaa/da/cmartin/CI/GDASApp/data")
prepend_path("PATH","/apps/contrib/NCEP/libs/hpc-stack/intel-2018.4/prod_util/1.2.2/bin")

execute{cmd="ulimit -s unlimited",modeA={"load"}}
