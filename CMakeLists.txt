# ------------------------------------------------------------------------- #
# Application for all the components needed for the GDAS system             #
# ------------------------------------------------------------------------- #

# Check for minimim cmake requirement
cmake_minimum_required( VERSION 3.20 FATAL_ERROR )

find_package(ecbuild 3.5 REQUIRED HINTS ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/../ecbuild)

project(GDASApp VERSION 1.0.0 LANGUAGES C CXX Fortran )

include(GNUInstallDirs)
enable_testing()

# Build type.
if(NOT CMAKE_BUILD_TYPE MATCHES "^(Debug|Release|RelWithDebInfo|MinSizeRel)$")
  message(STATUS "Setting build type to 'Release' as none was specified.")
  set(CMAKE_BUILD_TYPE
      "Release"
      CACHE STRING "Choose the type of build." FORCE)
  set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release"
                                               "MinSizeRel" "RelWithDebInfo")
endif()

# Find dependencies.
find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Include ecbuild_bundle macro
include( ecbuild_bundle )

# Enable MPI
set( ENABLE_MPI ON CACHE BOOL "Compile with MPI" )

# Handle user options.
option(BUILD_GDASBUNDLE "Build GDAS Bundle" ON)
option(CLONE_JCSDADATA "Clone JCSDA test data repositories" OFF)
option(WORKFLOW_TESTS "Include global-workflow dependent tests" OFF)

# Initialize bundle
# -----------------
ecbuild_bundle_initialize()

# Build bundle source code.
if(BUILD_GDASBUNDLE)

# jedi-cmake
  ecbuild_bundle( PROJECT jedicmake GIT "https://github.com/jcsda/jedi-cmake.git" TAG 1.4.0 RECURSIVE )
  include( jedicmake/cmake/Functions/git_functions.cmake )

# ECMWF libraries
  option("BUNDLE_SKIP_ECKIT" "Don't build eckit" "ON" ) # Skip eckit build unless user passes -DBUNDLE_SKIP_ECKIT=OFF
  option("BUNDLE_SKIP_FCKIT" "Don't build fckit" "ON") # Skip fckit build unless user passes -DBUNDLE_SKIP_FCKIT=OFF
  option("BUNDLE_SKIP_ATLAS" "Don't build atlas" "ON") # Skip atlas build unless user passes -DBUNDLE_SKIP_ATLAS=OFF

# turn off optional OOPS toy models
  option( ENABLE_LORENZ95_MODEL "Build LORENZ95 toy model" OFF )
  option( ENABLE_QG_MODEL "Build QG toy model" OFF )

  ecbuild_bundle( PROJECT eckit GIT "https://github.com/ecmwf/eckit.git" TAG 1.16.0 )
  ecbuild_bundle( PROJECT fckit GIT "https://github.com/ecmwf/fckit.git" TAG 0.9.2 )
  ecbuild_bundle( PROJECT atlas GIT "https://github.com/ecmwf/atlas.git" TAG 0.35.0 )

# External (required) observation operators
  option("BUNDLE_SKIP_CRTM" "Don't build CRTM" "OFF") # Don't build crtm unless user passes -DBUNDLE_SKIP_CRTM=OFF
  ecbuild_bundle( PROJECT crtm GIT "https://github.com/JCSDA/crtm.git"   TAG v2.4.1-jedi.1 )

# Build GSI-B
  option(BUILD_GSIBEC "Build GSI-B" OFF)
  if(BUILD_GSIBEC)
    ecbuild_bundle( PROJECT gsibec GIT "https://github.com/GEOS-ESM/GSIbec.git" TAG 1.1.2 )
  endif()

# Gibbs seawater
  ecbuild_bundle( PROJECT gsw GIT "https://github.com/jcsda-internal/GSW-Fortran.git" TAG 1a02eba )

# Core JEDI repositories
  ecbuild_bundle( PROJECT oops  GIT "https://github.com/jcsda/oops.git"  TAG 60f9392)
  ecbuild_bundle( PROJECT vader GIT "https://github.com/jcsda/vader.git" TAG 3d90d96 )
  ecbuild_bundle( PROJECT saber GIT "https://github.com/jcsda/saber.git" TAG 4f1956c )
  option(ENABLE_IODA_DATA "Obtain ioda test data from ioda-data repository (vs tarball)" ON)
  ecbuild_bundle( PROJECT ioda  GIT "https://github.com/jcsda/ioda.git" TAG 050d268  )
  option(ENABLE_UFO_DATA "Obtain ufo test data from ufo-data repository (vs tarball)" ON)
  ecbuild_bundle( PROJECT ufo   GIT "https://github.com/jcsda/ufo.git" TAG e41a1c9 )

# FMS and FV3 dynamical core
  ecbuild_bundle( PROJECT fms GIT "https://github.com/jcsda/FMS.git" TAG 1f73914 )
  ecbuild_bundle( PROJECT fv3 GIT "https://github.com/jcsda/GFDL_atmos_cubed_sphere.git" TAG 61450b4 )

# fv3-jedi and associated repositories
  ecbuild_bundle( PROJECT femps       GIT "https://github.com/jcsda/femps.git"                TAG cb39681 )
  ecbuild_bundle( PROJECT fv3-jedi-lm GIT "https://github.com/jcsda/fv3-jedi-linearmodel.git" TAG 05cc1ae )
  option(ENABLE_FV3_JEDI_DATA "Obtain fv3-jedi test data from fv3-jedi-data repository (vs tarball)" ON)
  ecbuild_bundle( PROJECT fv3-jedi    GIT "https://github.com/jcsda/fv3-jedi.git"             TAG b4bc841 )

# SOCA associated repositories
# TODO: Move the Icepack fork to EMC github
  set(BUILD_ICEPACK "ON" CACHE STRING "Build the icepack library")
  if ( BUILD_ICEPACK )
    ecbuild_bundle( PROJECT icepack GIT "https://github.com/JCSDA-internal/Icepack.git" BRANCH feature/ecbuild-new )
  endif()
  ecbuild_bundle( PROJECT mom6 GIT "https://github.com/jcsda-internal/MOM6.git" TAG 51ec489 RECURSIVE )
  ecbuild_bundle( PROJECT soca GIT "https://github.com/jcsda-internal/soca.git" TAG 5783fd7 )

  # Build JEDI/DA or other peripherals
  ecbuild_bundle( PROJECT gdas-utils SOURCE "./utils" )

# Build IODA converters
  option(BUILD_IODA_CONVERTERS "Build IODA Converters" ON)
  if(BUILD_IODA_CONVERTERS)
    ecbuild_bundle( PROJECT iodaconv GIT "https://github.com/JCSDA-internal/ioda-converters.git" TAG 01adb65 )
  endif()

# Land associated repositories
  ecbuild_bundle( PROJECT land-imsproc  GIT "https://github.com/NOAA-PSL/land-IMS_proc.git"  TAG 6373819 )
  ecbuild_bundle( PROJECT land-jediincr GIT "https://github.com/NOAA-PSL/land-apply_jedi_incr.git"  TAG 2923344)

# ioda, ufo, fv3-jedi, and saber test data
#---------------------------------
if(CLONE_JCSDADATA)

  # If IODA branch is being built set GIT_BRANCH_FUNC to IODA's current branch.
  # If a tagged version of IODA is being built set GIT_TAG_FUNC to ioda's current tag. In this case,
  # IODA test files will be download from UCAR DASH and ioda-data repo will not be cloned.
  # When LOCAL_PATH_JEDI_TESTFILES is set to the directory of IODA test files stored
  # in a local directory, ioda-data repo will not be cloned

    find_branch_name(REPO_DIR_NAME ioda)
  # When LOCAL_PATH_JEDI_TESTFILES is set to the directory of IODA test files stored
  # in a local directory, ioda-data repo will not be cloned
    if( NOT DEFINED ENV{LOCAL_PATH_JEDI_TESTFILES} AND NOT DEFINED GIT_TAG_FUNC )
      ecbuild_bundle( PROJECT ioda-data GIT "https://github.com/JCSDA-internal/ioda-data.git" BRANCH develop )

      # If IODA's current branch is available in ioda-data repo, that branch will be checked out
      branch_checkout (REPO_DIR_NAME ioda-data
                      BRANCH ${GIT_BRANCH_FUNC} )
    endif()

  # same procedure for ufo-data
    find_branch_name(REPO_DIR_NAME ufo)
    if( NOT DEFINED ENV{LOCAL_PATH_JEDI_TESTFILES} AND NOT DEFINED GIT_TAG_FUNC )
      ecbuild_bundle( PROJECT ufo-data GIT "https://github.com/JCSDA-internal/ufo-data.git" BRANCH develop )

      # If UFO's current branch is available in ioda-data repo, that branch will be checked out
      branch_checkout (REPO_DIR_NAME ufo-data
                      BRANCH ${GIT_BRANCH_FUNC} )
    endif()

  # same procedure for fv3-jedi-data
    find_branch_name(REPO_DIR_NAME fv3-jedi)
    if( NOT DEFINED ENV{LOCAL_PATH_JEDI_TESTFILES} AND NOT DEFINED GIT_TAG_FUNC )
      ecbuild_bundle( PROJECT fv3-jedi-data GIT "https://github.com/JCSDA-internal/fv3-jedi-data.git" BRANCH develop )

      # If fv3-jedi's current branch is available in ioda-data repo, that branch will be checked out
      branch_checkout (REPO_DIR_NAME fv3-jedi-data
                      BRANCH ${GIT_BRANCH_FUNC} )
    endif()

  endif(CLONE_JCSDADATA)

endif(BUILD_GDASBUNDLE)

# Install utility scripts.
add_subdirectory(ush)

# Include testing.
add_subdirectory(test)

# Finalize bundle
# ---------------
ecbuild_bundle_finalize()
