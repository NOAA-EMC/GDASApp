-- NOAA HPC Orion Modulefile for EVA
help([[
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

prepend_path("MODULEPATH", '/work/noaa/epic/role-epic/spack-stack/hercules/spack-stack-1.6.0/envs/unified-env/install/modulefiles/Core')

load("stack-intel/2021.9.0")
load("python/3.10.13")
load("proj/9.2.1")
load("py-matplotlib/3.7.3")
load("py-xarray/2023.7.0")
load("py-cartopy/0.21.1")
load("py-scipy/1.11.3")

local pyenvpath = "/work2/noaa/da/python/envs/"
local pyenvname = "eva"

local pyenvactivate = pathJoin(pyenvpath, pyenvname, "bin/activate")
if (mode() == "load") then
  local activate_cmd = "source "..pyenvactivate
  execute{cmd=activate_cmd, modeA={"load"}}
else
  if (mode() == "unload") then
    local deactivate_cmd = "deactivate"
    execute{cmd=deactivate_cmd, modeA={"unload"}}
  end
end

whatis("Name: ".. pkgName)
whatis("Version: " .. pkgVersion)
whatis("Category: EVA")
whatis("Description: Load all libraries needed for EVA")
