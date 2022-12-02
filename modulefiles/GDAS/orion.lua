-- NOAA HPC Orion Modulefile for GDASApp 
help([[
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

prepend_path("MODULEPATH", '/work/noaa/da/role-da/spack-stack/spack-stack-v1/envs/skylab-2.0.0-intel-2022.0.2/install/modulefiles/Core')

prepend_path("MODULEPATH", '/work2/noaa/da/python/opt/modulefiles/stack')

-- below two lines get us access to the spack-stack modules
load("stack-intel/2022.0.2")
load("stack-intel-oneapi-mpi/2021.5.1")
-- JCSDA has 'jedi-fv3-env/1.0.0', but we should load these manually as needed
load("cmake/3.22.1")
load("zlib/1.2.12")
load("curl/7.85.0")
load("git/2.28.0")
load("pkg-config/0.27.1")
load("hdf5/1.12.1")
load("parallel-netcdf/1.12.2")
load("netcdf-c/4.8.1")
load("nccmp/1.9.0.1")
load("netcdf-fortran/4.5.4")
load("nco/5.0.6")
load("parallelio/2.5.7")
load("wget/1.14")
load("boost/1.72.0")
load("bufr/11.7.1")
load("git-lfs/2.12.0")
load("ecbuild/3.6.5")
load("openjpeg/2.3.1")
load("eccodes/2.27.0")
load("eigen/3.4.0")
load("openblas/0.3.19")
load("eckit/1.19.0")
load("fftw/3.3.10")
load("fckit/0.9.5")
load("fiat/1.0.0")
load("ectrans/1.0.0")
load("atlas/0.30.0")
load("sp/2.3.3")
load("gsl-lite/0.37.0")
load("libjpeg/2.1.0")
load("krb5/1.15.1")
load("libtirpc/1.2.6")
load("hdf/4.2.15")
load("jedi-cmake/1.4.0")
load("libpng/1.6.37")
load("libxt/1.1.5")
load("libxmu/1.1.2")
load("libxpm/4.11.0")
load("libxaw/1.0.13")
load("udunits/2.2.28")
load("ncview/2.1.8")
load("netcdf-cxx4/4.3.1")
load("py-pybind11/2.8.1")
--load("crtm/v2.4_jedi")

load("hpc/1.2.0")
load("miniconda3/4.6.14")
load("gdasapp/1.0.0")

-- below is a hack because of cmake finding the wrong python...
setenv("CONDA_PREFIX", "/work2/noaa/da/python/opt/core/miniconda3/4.6.14/envs/gdasapp/")

setenv("CC","mpiicc")
setenv("FC","mpiifort")
setenv("CXX","mpiicpc")
local mpiexec = '/opt/slurm/bin/srun'
local mpinproc = '-n'
setenv('MPIEXEC_EXEC', mpiexec)
setenv('MPIEXEC_NPROC', mpinproc)

setenv('R2D2_CONFIG', '/work2/noaa/da/cmartin/GDASApp/R2D2_SHARED/config_orion.yaml')
setenv("CRTM_FIX","/work2/noaa/da/cmartin/GDASApp/fix/crtm")
setenv("GDASAPP_TESTDATA","/work2/noaa/da/cmartin/CI/GDASApp/data")
prepend_path("PATH","/apps/contrib/NCEP/libs/hpc-stack/intel-2018.4/prod_util/1.2.2/bin")

execute{cmd="ulimit -s unlimited",modeA={"load"}}

whatis("Name: ".. pkgName)
whatis("Version: " .. pkgVersion)
whatis("Category: GDASApp")
whatis("Description: Load all libraries needed for GDASApp")
