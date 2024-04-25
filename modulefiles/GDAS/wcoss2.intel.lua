help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

prepend_path("MODULEPATH", "/apps/dev/lmodules/core")

load("PrgEnv-intel/8.2.0")
load("cmake/3.20.2")
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
load("eckit/1.24.4")
load("fckit/0.11.0")
load("atlas/0.35.0")

-- hack for wxflow
--prepend_path("PYTHONPATH", "/scratch1/NCEPDEV/da/python/gdasapp/wxflow/20240307/src")

--setenv("CC","mpiicc")
--setenv("FC","mpiifort")
--setenv("CXX","mpiicpc")

--local mpiexec = '/apps/slurm/default/bin/srun'
--local mpinproc = '-n'
--setenv('MPIEXEC_EXEC', mpiexec)
--setenv('MPIEXEC_NPROC', mpinproc)

--setenv("CRTM_FIX","/scratch1/NCEPDEV/da/Cory.R.Martin/GDASApp/fix/crtm/2.4.0")
--setenv("GDASAPP_TESTDATA","/scratch1/NCEPDEV/da/Cory.R.Martin/CI/GDASApp/data")
--setenv("GDASAPP_UNIT_TEST_DATA_PATH", "/scratch1/NCEPDEV/da/Cory.R.Martin/CI/GDASApp/data/test")

whatis("Name: ".. pkgName)
whatis("Version: ".. pkgVersion)
whatis("Category: GDASApp")
whatis("Description: Load all libraries needed for GDASApp")
###### junk below #####

#!/bin/bash
# base modules
module load PrgEnv-intel/8.2.0
module load cmake/3.20.2
module load craype
module load cray-pals
module load git/2.29.0
module load intel/19.1.3.304
module load cray-mpich/8.1.12
module load hdf5/1.12.2 netcdf/4.7.4
module load udunits/2.2.28
module load eigen/3.4.0
module load boost/1.79.0
module load gsl-lite/v0.40.0
module load sp/2.4.0
module load python/3.8.6
#module load fms/2023.02.01
#module load crtm/2.4.0.1


module use /apps/dev/lmodules/core
module load ecbuild/3.7.0

module load qhull/2020.2
module load eckit/1.24.4
module load fckit/0.11.0
module load atlas/0.35.0

#export BOOST_ROOT=/apps/spack/boost/1.79.0/intel/19.1.3.304/rd3f57tsagr3zuosyl4dev7kbie6f43v
#export Boost_INCLUDE_DIR=$boost_ROOT/include/boost
#export eigen_ROOT=/apps/spack/eigen/3.4.0/intel/19.1.3.304/557xcyno3eksaklublyebh53ekc3kdwg
#export Eigen3_DIR=$eigen_ROOT/share/eigen3/cmake
#export eckit_ROOT=/apps/dev/eckit/install-1.24.4
#export fckit_ROOT=/apps/dev/fckit/install-0.11.0
#export atlas_ROOT=/apps/dev/atlas/install-0.35.0
#export atlas_ROOT=/lfs/h1/emc/nceplibs/noscrub/GDIT/atlas/install-0.35.0
#export Qhull_DIR=/lfs/h1/emc/nceplibs/noscrub/GDIT/testing/qhull-2020.2/build/
#export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/lfs/h1/emc/nceplibs/noscrub/GDIT/testing/qhull-2020.2/build/
export pybind11_ROOT=/apps/spack/python/3.8.6/intel/19.1.3.304/pjn2nzkjvqgmjw4hmyz43v5x4jbxjzpk/lib/python3.8/site-packages/pybind11/share/cmake/pybind1
