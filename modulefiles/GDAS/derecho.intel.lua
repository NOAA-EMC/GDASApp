help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

setenv("LMOD_TMOD_FIND_FIRST","yes")
prepend_path("MODULEPATH", "/lustre/desc1/scratch/epicufsrt/contrib/modulefiles_extra")
prepend_path("MODULEPATH", "/lustre/desc1/scratch/epicufsrt/contrib/modulefiles_extra")
prepend_path("MODULEPATH", "/glade/work/spk_stk_adm/contrib/spack-stack/derecho/spack-stack-2.2.0/envs/ue-oneapi-2025.3.2/modules/Core")

local stack_oneapi_ver=os.getenv("stack_oneapi_ver") or "2025.3.2"
load(pathJoin("stack-intel-oneapi-compilers", stack_oneapi_ver))

-- local stack_oneapi_mkl_ver=os.getenv("stack_oneapi_mkl_ver") or "2024.2.2"
-- load(pathJoin("stack-oneapi-mkl", stack_oneapi_mkl_ver))

local stack_cray_mpich_ver=os.getenv("stack_cray_mpich_ver") or "8.1.32"
load(pathJoin("stack-cray-mpich", stack_cray_mpich_ver))

local python_ver=os.getenv("python_ver") or "3.13.13"
local cmake_ver=os.getenv("cmake_ver") or "3.27.9"

load(pathJoin("python", python_ver))
load(pathJoin("cmake", cmake_ver))

load("gettext/1.0")
load("curl/8.20.0")
load("zlib/1.2.11")
load("git/2.47.0")
load("hdf5/2.1.0")
load("parallel-netcdf/1.14.1")
load("netcdf-c/4.9.2")
load("nccmp/1.9.0.1")
load("netcdf-fortran/4.6.1")
load("nco/5.3.9")
load("parallelio/2.6.2")
load("wget/1.20.3")
load("boost/1.84.0")
load("bufr/12.3.0")
load("git-lfs/3.5.1")
load("ecbuild/3.15.2")
load("openjpeg/2.3.1")
load("eccodes/2.33.0")
load("eigen/3.4.0")
load("eckit/2.0.7")
load("fckit/0.14.3")
load("fiat/2.0.0")
load("fms/2025.03-gfs-constants")
load("esmf/8.9.1")
load("ecmwf-atlas/0.46.0")
load("sp/2.5.0")
load("gsl-lite/0.41.0")
load("libjpeg/3.1.3")
load("krb5/1.19.2")
load("libtirpc/1.3.7")
load("hdf/4.2.15")
load("jedi-cmake/1.4.0")
load("libpng/1.6.55")
load("libxaw/1.0.16")
load("udunits/2.2.28")
load("ncview/2.1.9")
load("netcdf-cxx4/4.3.1")
load("json/3.12.0")
--load("crtm/v2.4_jedi")
-- load("rocoto/1.3.7")
load("prod_util/2.1.2")
load("grib-util/1.4.0")

load("py-jinja2/3.1.6")
load("py-netcdf4/1.7.2")
load("py-pybind11/2.13.6")
load("py-pycodestyle/2.14.0")
load("py-pyyaml/6.0.3")
load("py-scipy/1.17.1")
load("py-xarray/2026.4.0")
load("py-f90nml/1.4.3")
load("py-pip/26.1")
load("py-click/8.3.1")
load("py-wheel/0.45.1")

setenv("CC","cc")
setenv("CXX","CC")
setenv("FC","ftn")
setenv("I_MPI_CC", "icx")
setenv("I_MPI_CXX", "icpx")
setenv("I_MPI_F90", "ifx")

local mpiexec = 'mpiexec'
local mpinproc = '-n'
setenv('MPIEXEC_EXEC', mpiexec)
setenv('MPIEXEC_NPROC', mpinproc)

setenv("CRTM_FIX","/lustre/desc1/p/nral0032/global/data/fix/crtm/v2.4.0.2")

whatis("Name: ".. pkgName)
whatis("Version: ".. tostring(pkgVersion))
whatis("Category: GDASApp")
whatis("Description: Load all libraries needed for GDASApp")
