help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

prepend_path("MODULEPATH", "/contrib/spack-stack-rocky8/spack-stack-1.6.0/envs/ue-intel/install/modulefiles/Core")
--prepend_path("MODULEPATH", "/contrib/spack-stack-rocky8/spack-stack-1.6.0/envs/gsi-addon-env/install/modulefiles/Core")
--prepend_path("MODULEPATH", "/apps/modules/modulefiles")

gnu_ver=os.getenv("gnu_ver") or ""
load(pathJoin("gnu", gnu_ver))

stack_intel_ver=os.getenv("stack_intel_ver") or "2021.10.0"
load(pathJoin("stack-intel", stack_intel_ver))

stack_intel_oneapi_mpi_ver=os.getenv("stack_intel_oneapi_mpi_ver") or "2021.10.0"
load(pathJoin("stack-intel-oneapi-mpi", stack_intel_oneapi_mpi_ver))

unload(pathJoin("gnu", gnu_ver))

cmake_ver=os.getenv("cmake_ver") or "3.23.1"
load(pathJoin("cmake", cmake_ver))

load("GDAS/gdas_common")

setenv("CC","mpiicc")
setenv("FC","mpiifort")
setenv("CXX","mpiicpc")

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
