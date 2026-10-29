help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion() or "1.0"
local pkgNameVer = myModuleFullName()

prepend_path("MODULEPATH", "/opt/intel/oneapi/mpi/2021.18/etc/modulefiles/mpi")
prepend_path("MODULEPATH", "/lfs/work/alexander_richert/stack/spack-stack/envs/nco-core-gcc-11.5.0/modules_flat/Core")
prepend_path("MODULEPATH", "/lfs/work/alexander_richert/stack/spack-stack/envs/nco-sci-oneapi-2026.1.0/modules_flat/Core")

load("mpi/2021.18")
load("mkl/2023.2.0")

load("pmix/5.0.11")

load("cmake/3.31.11")
load("python/3.11.15")

load("git/2.53.0")
load("git-lfs/3.7.1")

load("zstd/1.5.7")
load("gettext/1.0")
load("curl/8.20.0")
load("hdf5/1.14.5")
load("parallel-netcdf/1.12.3")
load("netcdf-c/4.9.2")
load("nccmp/1.9.0.1")
load("netcdf-fortran/4.6.1")
load("nco/5.3.9")
load("parallelio/2.6.2")
load("wget/1.25.0")
load("boost/1.90.0")
load("ecbuild/3.12.0")
load("eccodes/2.33.0")
load("eigen/3.4.0")
load("openblas/0.3.33")
load("eckit/1.32.3")
load("fckit/0.14.1")
load("fms/2025.03-gfs-constants")
load("python-venv/1.0")
load("py-pyyaml/6.0.3")
load("glibc/2.34")
load("esmf/8.8.0")
load("ecmwf-atlas/0.44.1-extraopts")
load("sp/2.5.0")
load("ip/5.4.0")
load("gsl-lite/0.41.0")
load("libjpeg/3.1.3")
load("krb5/1.22.2")
load("libtirpc/1.3.7")
load("hdf/4.2.15")
load("jedi-cmake/1.4.0")
load("libpng/1.6.55")
load("udunits/2.2.28")
load("ncview/2.1.9")
load("netcdf-cxx4/4.3.1")
load("json/3.12.0")
--load("crtm/3.1.2")
--load("crtm-fix/3.1.2.0")
-- Do not load prod_util when running ecflow
--local is_ecf = os.getenv("ECF_JOB") ~= nil
--if not is_ecf then
--    load("prod_util/2.0.14")
--end

load("py-setuptools/73.0.1")
load("py-numpy/1.26.4")
load("bufr/12.3.0")

load("py-markupsafe/3.0.2")
load("py-jinja2/3.1.6")
load("py-cftime/1.6.4")
load("py-certifi/2026.2.25")
load("py-netcdf4/1.7.2")
load("py-pybind11/3.0.2")
load("py-pycodestyle/2.14.0")
load("py-pyyaml/6.0.3")
load("py-scipy/1.17.1")

load("py-setuptools/73.0.1")
load("py-six/1.17.0")
load("py-python-dateutil/2.9.0.post0")
load("py-pandas/3.0.3")
load("py-packaging/26.2")
load("py-xarray/2022.3.0")
load("py-f90nml/1.4.3")
load("py-pip/26.1")
load("py-click/8.1.8")
load("py-wheel/0.45.1")

setenv("CC","mpiicx")
setenv("CXX","mpiicpx")
setenv("FC","mpiifx")
setenv("I_MPI_CC", "icx")
setenv("I_MPI_CXX", "icpx")
setenv("I_MPI_F90", "ifx")

local mpiexec = 'usr/bin/srun'
local mpinproc = '-n'
setenv('MPIEXEC_EXEC', mpiexec)
setenv('MPIEXEC_NPROC', mpinproc)

setenv("CRTM_FIX","/home/russ_treadon_hpc_noaa_gov/GDASApp/fix/crtm/2.4.0")
setenv("GDASAPP_TESTDATA","/home/russ_treadon_hpc_noaa_gov/GDASApp/testdata")
setenv("GDASAPP_UNIT_TEST_DATA_PATH", "/home/russ_treadon_hpc_noaa_gov/GDASApp/unittestdata")

whatis("Name: ".. pkgName)
whatis("Version: ".. pkgVersion)
whatis("Category: GDASApp")
whatis("Description: Load all libraries needed for GDASApp")
