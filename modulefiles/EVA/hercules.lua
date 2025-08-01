-- NOAA HPC Orion Modulefile for EVA
help([[
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

prepend_path("MODULEPATH", '/work2/noaa/da/python/opt/modulefiles/stack')

load("hpc/1.2.0")
load("miniconda3/4.6.14")
load("eva/1.0.0")

whatis("Name: ".. pkgName)
whatis("Version: " .. pkgVersion)
whatis("Category: EVA")
whatis("Description: Load all libraries needed for EVA")
