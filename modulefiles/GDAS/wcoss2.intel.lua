help([[
Load environment for running the GDAS application with Intel compilers and MPI.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion() or "1.0"
local pkgNameVer = myModuleFullName()

local PrgEnv_intel_ver=os.getenf("PrgEnv_intel_ver") or "8.5.0"
local intel_ver=os.getenv("intel_ver") or "19.1.3.304"
local craype_ver=os.getenv("craype_ver") or "2.7.17"
local cmake_ver=os.getenv("cmake_ver") or "3.27.9"
local cray_pals_ver=os.getenv("cray_pals_ver") or "1.3.2"
local git_ver=os.getenv("git_ver") or "2.29.0"
local cray_mpich_ver=os.getenv("cray_mpich_ver") or "8.1.19"
local hdf5_ver=os.getenv("hdf5_ver") or "1.14.0"
local pnetcdf_ver=os.getenv("pnetcdf_ver") or "1.12.2"
local netcdf_ver=os.getenv("netcdf_ver") or "4.9.2"
local udunits_ver=os.getenv("udunits_ver") or "2.2.28"
local eigen_ver=os.getenv("eigen_ver") or "3.4.0"
local boost_ver=os.getenv("boost_ver") or "1.79.0"
local gsl_lite_ver=os.getenv("gsl_lite_ver") or "v0.40.0"
local sp_ver=os.getenv("sp_ver") or "2.4.0"
local python_ver=os.getenv("python_ver") or "3.12.0"
local ve_gfs_ver=os.getenv("ve_gfs_ver") or "17.0"
local ecbuild_ver=os.getenv("ecbuild_ver") or "3.7.2"
local qhull_ver=os.getenv("qhull_ver") or "2020.2"
local nco_ver=os.getenv("nco_ver") or "5.2.4"
local gsl_ver=os.getenv("gsl_ver") or "2.7"
local bufr_ver=os.getenv("bufr_ver") or "12.3.0"
local fms_ver=os.getenv("fms_ver") or "2024.01"
local esmf_ver=os.getenv("esmf_ver") or "8.8.0"
local eckit_ver=os.getenv("eckit_ver") or "1.28.0"
local fckit_ver=os.getenv("fckit_ver") or "0.13.1"
local atlas_ver=os.getenv("atlas_ver") or "0.39.0"

load(pathJoin("PrgEnv-intel", PrgEnv_intel_ver))
load(pathJoin("cmake", cmake_ver))
load(pathJoin("craype", craype_ver))
load(pathJoin("cray-pals", cray_pals_ver))
load(pathJoin("git", git_ver))
load(pathJoin("intel", intel_ver))
load(pathJoin("cray-mpich", cray_mpich_ver))
load(pathJoin("hdf5-D", hdf5_ver))
load(pathJoin("pnetcdf-D", pnetcdf_ver))
load(pathJoin("netcdf-D", netcdf_ver))
load(pathJoin("udunits", udunits_ver))
load(pathJoin("eigen", eigen_ver))
load(pathJoin("boost", boost_ver))
load(pathJoin("gsl-lite", gsl_lite_ver))
load(pathJoin("sp", sp_ver))
load(pathJoin("python", python_ver))
load(pathJoin("ve/gfs", ve_gfs_ver))
load(pathJoin("ecbuild", ecbuild_ver))
load(pathJoin("qhull", qhull_ver))
load(pathJoin("nco", nco_ver))
load(pathJoin("gsl", gsl_ver)) 
load(pathJoin("bufr", bufr_ver)) 
load(pathJoin("fms-D", fms_ver))
load(pathJoin("esmf-D", esmf_ver))
load(pathJoin("eckit", eckit_ver))
load(pathJoin("fckit", fckit_ver))
load(pathJoin("atlas", atlas_ver))

setenv("CC","cc")
setenv("CXX","CC")
setenv("FC","ftn")

whatis("Name: ".. pkgName)
whatis("Version: ".. pkgVersion)
whatis("Category: GDASApp")
whatis("Description: Load all libraries needed for GDASApp")
