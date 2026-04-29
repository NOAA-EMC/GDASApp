help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
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
load("python/3.8.6")
load("ecbuild/3.7.0")
load("qhull/2020.2")
load("eckit/1.28.3")
load("fckit/0.13.2")
load("atlas/0.44.1")
load("nccmp")
load("nco/5.2.4")
load("gsl/2.7")
load("prod_util/2.0.14")
load("bufr/12.1.0")
load("fms-D/2024.01")

local mpiexec = '/pe/intel/compilers_and_libraries_2020.4.304/linux/mpi/intel64/bin/mpirun'
local mpinproc = '-n'
setenv('MPIEXEC_EXEC', mpiexec)
setenv('MPIEXEC_NPROC', mpinproc)

whatis("Name: ".. pkgName)
whatis("Version: ".. pkgVersion)
whatis("Category: GDASApp")
whatis("Description: Load all libraries needed for GDASApp")
