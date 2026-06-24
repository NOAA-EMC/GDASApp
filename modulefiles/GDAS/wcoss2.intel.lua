help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion() or "1.0"
local pkgNameVer = myModuleFullName()

prepend_path("MODULEPATH", "/apps/dev/lmodules/core")

load("PrgEnv-intel/8.5.0")
load("cmake/3.27.9")
load("craype")
load("cray-pals")
load("git/2.29.0")
load("intel/19.1.3.304")
load("cray-mpich/8.1.19")
load("hdf5-D/1.14.0")
load("pnetcdf-D/1.12.2")
load("netcdf-D/4.9.2")
load("udunits/2.2.28")
load("eigen/3.4.0")
load("boost/1.79.0")
load("gsl-lite/v0.40.0")
load("sp/2.4.0")
load("python/3.12.0")
load("ve/gcafs/1.0.0")
load("ecbuild/3.7.0")
load("qhull/2020.2")
load("nco/5.2.4") 
load("gsl/2.7") 
load("prod_util/2.0.14")
load("bufr/12.3.0") 
load("fms-D/2024.01")
load("esmf-D/8.8.0")
load("eckit/1.28.0")
load("fckit/0.13.1")
load("atlas/0.39.0")

setenv("CC","cc")
setenv("CXX","CC")
setenv("FC","ftn")

local mpiexec = '/opt/cray/pals/1.3.2/bin/mpirun'
local mpinproc = '-n'
setenv('MPIEXEC_EXEC', mpiexec)
setenv('MPIEXEC_NPROC', mpinproc)

setenv("CRTM_FIX","/lfs/h2/emc/da/noscrub/emc.da/GDASApp/fix/crtm/2.4.0")
setenv("GDASAPP_TESTDATA","/lfs/h2/emc/da/noscrub/emc.da/GDASApp/testdata")
setenv("GDASAPP_UNIT_TEST_DATA_PATH", "/lfs/h2/emc/da/noscrub/emc.da/GDASApp/unittestdata")

whatis("Name: ".. pkgName)
whatis("Version: ".. pkgVersion)
whatis("Category: GDASApp")
whatis("Description: Load all libraries needed for GDASApp")
