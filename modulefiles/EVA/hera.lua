help([[
Load environment for running EVA.
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

conflict(pkgName)

prepend_path("MODULEPATH", '/scratch1/NCEPDEV/da/python/opt/modulefiles/stack')

load("hpc/1.2.0")
load("miniconda3/4.6.14")
load("eva/1.0.0")

whatis("Name: ".. pkgName)
whatis("Version: ".. pkgVersion)
whatis("Category: EVA")
whatis("Description: Load all libraries needed for EVA")
