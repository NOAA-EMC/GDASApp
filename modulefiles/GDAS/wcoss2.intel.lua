help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

prepend_path("MODULEPATH", "/apps/dev/lmodules/core")

load("PrgEnv-intel/8.2.0")
load("cmake/3.30.5")
load("craype")
load("cray-pals")
load("git/2.29.0")
load("intel/19.1.3.304")
load("cray-mpich/8.1.12")
load("hdf5/1.12.2")
load("netcdf/4.7.4")
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
load("nco/5.0.6")
load("gsl/2.7")
load("prod_util/2.0.14")
load("bufr/12.1.0")
load("fms-D/2024.01")

-- hack for pybind11
setenv("pybind11_ROOT", "/apps/spack/python/3.8.6/intel/19.1.3.304/pjn2nzkjvqgmjw4hmyz43v5x4jbxjzpk/lib/python3.8/site-packages/pybind11/share/cmake/pybind11")

-- hack for git-lfs
prepend_path("PATH", "/apps/spack/git-lfs/2.11.0/gcc/11.2.0/m6b6nl5kfqngfteqbggydc7kflxere3s/bin")

-- hack for eigen
setenv("Eigen3_DIR", "/apps/spack/eigen/3.4.0/intel/19.1.3.304/557xcyno3eksaklublyebh53ekc3kdwg/share/eigen3/cmake/")

-- hack for FMS
setenv("fms_DIR", "/apps/prod/hpc-stack/i-19.1.3.304__m-8.1.19__h-1.14.0__n-4.9.2__p-2.5.10__e-8.8.0_pnetcdf/intel-19.1.3.304/cray-mpich-8.1.19/fms/2024.01/lib/cmake/fms/")

local mpiexec = '/pe/intel/compilers_and_libraries_2020.4.304/linux/mpi/intel64/bin/mpirun'
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
