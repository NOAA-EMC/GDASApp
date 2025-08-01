help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

prepend_path("MODULEPATH", "/opt/spack-stack/spack-stack-1.9.1/envs/unified-env/install/modulefiles/Core")

stack_oneapi_ver=os.getenv("stack_oneapi_ver") or "2024.2.0"
stack_impi_ver=os.getenv("stack_impi_ver") or "2021.13"

load(pathJoin("stack-oneapi", stack_oneapi_ver))
load(pathJoin("stack-intel-oneapi-mpi", stack_impi_ver))

load("gdas_common.lua")

setenv("CC","/apps/oneapi/mpi/latest/bin/mpiicx")
setenv("CXX","/apps/oneapi/mpi/latest/bin/mpiicpx")
setenv("FC","/apps/oneapi/mpi/latest/bin/mpiifort")
setenv("I_MPI_CC", "/apps/oneapi/compiler/2024.2/bin/icx")
setenv("I_MPI_CXX", "/apps/oneapi/compiler/2024.2/bin/icpx")
setenv("I_MPI_F90", "/apps/oneapi/compiler/2024.2/bin/ifort")

local mpiexec = '/apps/slurm/default/bin/srun'
local mpinproc = '-n'
setenv('MPIEXEC_EXEC', mpiexec)
setenv('MPIEXEC_NPROC', mpinproc)

setenv("CRTM_FIX","/contrib/global-workflow-shared-data/GDASApp/fix/crtm/2.4.0")
setenv("GDASAPP_TESTDATA","/contrib/global-workflow-shared-data/GDASApp/testdata")
setenv("GDASAPP_UNIT_TEST_DATA_PATH", "/contrib/global-workflow-shared-data/GDASApp/unittestdata")

whatis("Name: ".. pkgName)
whatis("Version: ".. pkgVersion)
whatis("Category: GDASApp")
whatis("Description: Load all libraries needed for GDASApp")
