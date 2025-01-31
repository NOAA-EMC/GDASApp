help([[
Load environment for running EVA.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

conflict(pkgName)

prepend_path("MODULEPATH", "/contrib/spack-stack//spack-stack-1.6.0/envs/unified-env-rocky8/install/modulefiles/Core")
load("stack-intel/2021.5.0")
load("python/3.10.13")
load("proj/9.2.1")

local pyenvpath = "/scratch1/NCEPDEV/da/python/envs/"
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
whatis("Version: ".. pkgVersion)
whatis("Category: EVA")
whatis("Description: Load all libraries needed for EVA")
