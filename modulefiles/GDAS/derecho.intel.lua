help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

setenv("LMOD_TMOD_FIND_FIRST","yes")
prepend_path("MODULEPATH", "/lustre/desc1/scratch/epicufsrt/contrib/modulefiles_extra")
prepend_path("MODULEPATH", "/lustre/desc1/scratch/epicufsrt/contrib/modulefiles_extra")
prepend_path("MODULEPATH", "/glade/work/epicufsrt/contrib/spack-stack/derecho/spack-stack-1.9.2/envs/ue-oneapi-2024.2.1/install/modulefiles/Core")

local stack_oneapi_ver=os.getenv("stack_oneapi_ver") or "2024.2.1"
load(pathJoin("stack-oneapi", stack_oneapi_ver))

-- local stack_oneapi_mkl_ver=os.getenv("stack_oneapi_mkl_ver") or "2024.2.2"
-- load(pathJoin("stack-oneapi-mkl", stack_oneapi_mkl_ver))

stack_impi_ver=os.getenv("stack_cray_mpich_ver") or "8.1.29"
load(pathJoin("stack-cray-mpich", stack_cray_mpich_ver))

local python_ver=os.getenv("python_ver") or "3.11.7"
local cmake_ver=os.getenv("cmake_ver") or "3.27.9"

load(pathJoin("python", python_ver))
load(pathJoin("cmake", cmake_ver))

load("gettext/0.22.5")
load("curl/8.10.1")
load("zlib/1.2.11")
load("git/2.47.0")
load("hdf5/1.14.3")
load("parallel-netcdf/1.12.3")
load("netcdf-c/4.9.2")
load("nccmp/1.9.1.0")
load("netcdf-fortran/4.6.1")
load("nco/5.2.4")
load("parallelio/2.6.2")
load("wget/1.20.3")
load("boost/1.84.0")
load("bufr/12.1.0")
load("git-lfs/3.5.1")
load("ecbuild/3.7.2")
load("openjpeg/2.3.1")
load("eccodes/2.33.0")
load("eigen/3.4.0")
-- load("openblas/0.3.28")
load("eckit/1.28.3")
load("fckit/0.13.2")
load("fiat/1.4.1")
load("fms/2024.02")
load("esmf/8.8.0")
load("atlas/0.40.0")
load("sp/2.5.0")
load("gsl-lite/0.37.0")
load("libjpeg/2.1.0")
load("krb5/1.19.2")
load("libtirpc/1.3.3")
load("hdf/4.2.15")
load("jedi-cmake/1.4.0")
load("libpng/1.6.37")
load("libxt/1.3.0")
load("libxmu/1.2.1")
load("libxpm/3.5.17")
load("libxaw/1.0.16")
load("udunits/2.2.28")
load("ncview/2.1.9")
load("netcdf-cxx4/4.3.1")
load("json/3.11.3")
--load("crtm/v2.4_jedi")
-- load("rocoto/1.3.7")
load("prod_util/2.1.1")
load("grib-util/1.4.0")

load("py-jinja2/3.1.4")
load("py-netcdf4/1.7.1.post2")
load("py-pybind11/2.13.5")
load("py-pycodestyle/2.11.0")
load("py-pyyaml/6.0.2")
load("py-scipy/1.14.1")
load("py-xarray/2024.7.0")
load("py-f90nml/1.4.3")
load("py-pip/23.1.2")
load("py-click/8.1.7")
load("py-wheel/0.41.2")

setenv("CC","cc")
setenv("CXX","CC")
setenv("FC","ftn")
setenv("I_MPI_CC", "icx")
setenv("I_MPI_CXX", "icpx")
setenv("I_MPI_F90", "ifort")

local mpiexec = 'mpiexec'
local mpinproc = '-n'
setenv('MPIEXEC_EXEC', mpiexec)
setenv('MPIEXEC_NPROC', mpinproc)

setenv("CRTM_FIX","/lustre/desc1/p/nral0032/global/data/fix/crtm/v2.4.0.2")

whatis("Name: ".. pkgName)
whatis("Version: ".. tostring(pkgVersion))
whatis("Category: GDASApp")
whatis("Description: Load all libraries needed for GDASApp")
