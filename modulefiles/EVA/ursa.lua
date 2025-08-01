help([[
Load python virtual environment for obs-monitor
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()

conflict(pkgName)

-- Load dependencies
prepend_path("MODULEPATH", "/contrib/spack-stack/spack-stack-1.9.2/envs/ue-oneapi-2024.2.1/install/modulefiles/Core")

load("stack-oneapi/2024.2.1")
load("stack-intel-oneapi-mpi/2021.13")
load("intel-oneapi-mkl/2024.2.1")
load("stack-python/3.11.7")
load("rocoto/1.3.7")

-- Python packages
load("py-jinja2/3.1.4")
load("py-netcdf4/1.7.1.post2")
load("py-pybind11/2.13.5")
load("py-pycodestyle/2.11.0")
load("py-pyyaml/6.0.2")
load("py-scipy/1.14.1")
load("py-xarray/2024.7.0")
load("py-pip/23.1.2")
load("py-matplotlib/3.7.4")
load("py-cartopy/0.24.1")
load("proj/9.4.1")
load("py-wxflow/0.2.0")

-- Set the venv path
local venv_root = "/scratch3/NCEPDEV/da/Edward.Safford/noscrub/python/envs/obs-mon"
local bin_path  = pathJoin(venv_root, "bin")
local lib_path  = pathJoin(venv_root, "lib/python3.11/site-packages")  -- adjust Python version if needed

-- Modify environment variables to emulate virtualenv activation
prepend_path("PATH", bin_path)
prepend_path("PYTHONPATH", lib_path)

-- Optional: If you want to make this environment more self-contained
setenv("VIRTUAL_ENV", venv_root)

whatis("Name: " .. pkgName)
whatis("Version: " .. tostring(pkgVersion))
whatis("Category: Obs-monitor")
whatis("Description: Load all libraries needed for obs-monitor")