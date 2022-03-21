-- NOAA HPC Orion Modulefile for UFS-DA
help([[
]])

local pkgName    = myModuleName()
local pkgVersion = myModuleVersion()
local pkgNameVer = myModuleFullName()

local jedi_opt = '/work/noaa/da/jedipara/opt/modules'
setenv('JEDI_OPT', jedi_opt)
local jedi_core = pathJoin(jedi_opt, 'modulefiles/core')
prepend_path("MODULEPATH", jedi_core)

load('jedi/intel-impi')

local mpiexec = '/opt/slurm/bin/srun'
local mpinproc = '-n'
setenv('MPIEXEC_EXEC', mpiexec)
setenv('MPIEXEC_NPROC', mpinproc)

-- add R2D2 and SOLO to PYTHONPATH
prepend_path("PYTHONPATH", "/work2/noaa/da/cmartin/UFSDA/python/local/lib/python3.9/site-packages")
-- add R2D2 to path
prepend_path("PATH", "/work2/noaa/da/cmartin/UFSDA/python/local/bin")

whatis("Name: ".. pkgName)
whatis("Version: " .. pkgVersion)
whatis("Category: UFS-DA")
whatis("Description: Load JEDI-Stack for UFS-DA")
