# GDASApp - Global Data Assimilation System Application

NOAA's weather and ocean data assimilation system built on the JEDI (Joint Effort for Data assimilation Integration) framework. This application integrates atmospheric, oceanic, sea-ice, aerosol, and land data assimilation capabilities.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Basic Setup (Works in GitHub CI)
- Install Python dependencies:
  - `pip install --upgrade pip`
  - `pip install pycodestyle netCDF4 xarray wxflow`
- Install wxflow (NOAA workflow utility):
  - `git clone https://github.com/NOAA-EMC/wxflow.git`
  - `cd wxflow && git checkout develop && pip install .`
- Install ecBuild (ECMWF CMake framework):
  - `git clone https://github.com/ecmwf/ecbuild.git`
  - `cd ecbuild && git checkout 3.8.2`
  - `mkdir bootstrap && cd bootstrap`
  - `../bin/ecbuild .. && sudo make install`

### Initialize Submodules (Required for full build)
- `git submodule update --init --recursive` -- takes 2-3 minutes. NEVER CANCEL.

### Build Options
**Minimal Build (for development/CI):**
- Create build directory: `mkdir build && cd build`
- Set test data path: `export GDASAPP_UNIT_TEST_DATA_PATH=/tmp/gdasapp-testdata && mkdir -p $GDASAPP_UNIT_TEST_DATA_PATH`
- Configure: `cmake -DBUILD_GDASBUNDLE=OFF /path/to/GDASApp` -- takes 1 minute
- Build: `make` -- takes under 1 minute
- Test: `ctest --output-on-failure` -- takes 3 seconds

**Full Bundle Build (HPC only):**
- Requires HPC system modules (Hera, Orion, Hercules, WCOSS2, etc.)
- Use `./build.sh -t <machine>` where machine is hera, orion, hercules, wcoss2, etc.
- Full build takes 60+ minutes. NEVER CANCEL. Set timeout to 120+ minutes.
- Requires significant computational resources and specialized libraries

### On HPC Systems
- Detect machine: `source ush/detect_machine.sh`
- Load modules: `source ush/module-setup.sh && module use modulefiles && module load GDAS/$MACHINE_ID.intel`
- Build: `./build.sh -t $MACHINE_ID` -- 60+ minutes. NEVER CANCEL. Set timeout to 120+ minutes.

## Testing and Validation

### Unit Tests (Always run these)
- Run coding standards: `pycodestyle -v --config ./.pycodestyle ./ush ./scripts ./test` -- takes 2 seconds
- Run YAML validation: `python3 ush/check_yaml_keys.py test/testinput/check_yaml_keys_ref.yaml test/testinput/check_yaml_keys_test.yaml`
- Run minimal unit tests: `cd build && ctest --output-on-failure` -- takes 3 seconds

### Integration Tests (HPC only)
- Requires global-workflow integration
- Tests may require NOAA test data from /scratch filesystems
- Some tests disabled due to network/data access requirements

### Validation Scenarios
- ALWAYS validate changes by running Python syntax checks
- Check YAML configuration files for validity
- Verify submodule initialization when working with full bundle
- Test ocean/atmosphere/land DA component integration on HPC systems

## Common Tasks

### Repository Structure
```
GDASApp/
├── build.sh              # Main build script for HPC systems
├── CMakeLists.txt         # Build configuration
├── bundle/               # JEDI bundle configuration
├── ci/                   # Continuous integration scripts
├── mains/                # Main executables
├── modulefiles/          # HPC module files
├── parm/                 # Parameter files and JCB configurations
├── scripts/              # Workflow scripts  
├── sorc/                 # Source code submodules
├── test/                 # Test configurations and data
├── ush/                  # Utility shell and Python scripts
└── utils/                # Utility programs
```

### Key Files and Locations
- Build configuration: `CMakeLists.txt`, `bundle/CMakeLists.txt`
- HPC modulefiles: `modulefiles/GDAS/<machine>.intel.lua` 
- Machine detection: `ush/detect_machine.sh`
- Python utilities: `ush/` directory
- Test configs: `test/testinput/`
- CI workflows: `.github/workflows/`

### Development Workflow
- Always work against `dev/gdasapp` branch of global-workflow when needed
- PRs in GDASApp must have matching branch names with global-workflow PRs
- For global-workflow-only changes, create dummy commit: `git commit --allow-empty -m "Dummy commit"`

## Limitations and Warnings

### What Works in GitHub CI
- Minimal builds with `-DBUILD_GDASBUNDLE=OFF`
- Python syntax and coding standards checks
- Basic unit tests (2 tests pass)
- Configuration validation

### What Requires HPC Systems
- Full JEDI bundle builds (`-DBUILD_GDASBUNDLE=ON`)
- Complete test suite execution
- Ocean/atmosphere/land DA workflow testing
- Integration with global-workflow
- Access to NOAA test datasets

### Build Timing Expectations
- Submodule initialization: 2-3 minutes
- Minimal build: under 2 minutes total
- Full HPC build: 60+ minutes. NEVER CANCEL. Always set timeout to 120+ minutes.
- Python checks: under 10 seconds
- Unit tests: under 10 seconds

### Network Dependencies
- Some test data downloads fail in restricted environments
- Full functionality requires access to NOAA FTP servers
- Submodule cloning requires GitHub access

## Critical Reminders
- ***NEVER CANCEL BUILDS OR LONG-RUNNING COMMANDS*** - Full builds may take 60+ minutes
- ***ALWAYS*** run `pycodestyle` before committing changes
- Initialize submodules before attempting full builds
- Use appropriate machine-specific modulefiles on HPC systems
- Test data downloads may fail in CI - this is expected
- Always validate YAML configuration files