help([[
Load environment for running EVA.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

conflict(pkgName)

load("PrgEnv-intel/8.2.0")
load("craype")
load("cray-pals")
load("git/2.29.0")
load("intel/19.1.3.304")
load("python/3.10.4")
load("ve/evs/1.0")

append_path("PATH", "/lfs/h2/emc/da/noscrub/emc.da/eva/opt/bin")
append_path("PYTHONPATH", "/lfs/h2/emc/da/noscrub/emc.da/eva/opt/")

whatis("Name: ".. pkgName)
whatis("Version: ".. pkgVersion)
whatis("Category: EVA")
whatis("Description: Load all libraries needed for EVA")
