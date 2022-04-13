-- NOAA HPC Orion Modulefile for GDASApp 
help([[
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

local jedi_opt = '/work/noaa/da/jedipara/opt/modules'
setenv('JEDI_OPT', jedi_opt)
local jedi_core = pathJoin(jedi_opt, 'modulefiles/core')
prepend_path("MODULEPATH", jedi_core)

prepend_path("MODULEPATH", '/work2/noaa/da/python/opt/modulefiles/stack')

load("cmake/3.22.1")
load("git/2.28.0")
load("git-lfs/2.13.2")

load("jedi-intel/2020.2")
load("mkl/2020.2")
load("szip/2.1.1")
load("zlib/1.2.11")
load("udunits/2.2.28")
load("gsl_lite/0.37.0")
load("jedi-impi/2020.2")

load("hdf5/1.12.0")
load("pnetcdf/1.12.1")
load("netcdf/4.7.4")

load("boost-headers/1.68.0")
load("eigen/3.3.7")
load("bufr/noaa-emc-11.5.0")
load("pybind11/2.7.0")
load("nccmp/1.8.7.0")
load("pio/2.5.1-debug")

load("ecbuild/ecmwf-3.6.1")
load("eckit/ecmwf-1.16.0")
load("fckit/ecmwf-0.9.2")
load("atlas/ecmwf-0.24.1")

load("hpc/1.2.0")
load("miniconda3/4.6.14")
load("gdasapp/1.0.0")

setenv("CC","mpiicc")
setenv("FC","mpiifort")
setenv("CXX","mpiicpc")
local mpiexec = '/opt/slurm/bin/srun'
local mpinproc = '-n'
setenv('MPIEXEC_EXEC', mpiexec)
setenv('MPIEXEC_NPROC', mpinproc)

setenv('R2D2_CONFIG', '/work2/noaa/da/cmartin/GDASApp/R2D2_SHARED/config_orion.yaml')

execute{cmd="ulimit -s unlimited",modeA={"load"}}

whatis("Name: ".. pkgName)
whatis("Version: " .. pkgVersion)
whatis("Category: GDASApp")
whatis("Description: Load all libraries needed for GDASApp")
