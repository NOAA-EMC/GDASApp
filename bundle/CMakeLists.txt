# ------------------------------------------------------------------------- #
# JEDI GDAS Bundle             #
# ------------------------------------------------------------------------- #

# Check for minimim cmake requirement
cmake_minimum_required( VERSION 3.20 FATAL_ERROR )

find_package(ecbuild 3.5 REQUIRED HINTS ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/../ecbuild)

project(GDAS-bundle VERSION 1.0.0 LANGUAGES C CXX Fortran )

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
option(BUILD_JEDI "Build JEDI repositories in the bundle" ON)
option(BUILD_GDAS_JEDI "Build JEDI repositories in the bundle" ON)
option(CLONE_JCSDADATA "Clone JCSDA test data repositories" OFF)
option(WORKFLOW_TESTS "Include global-workflow dependent tests" OFF)

# Initialize bundle
# -----------------
ecbuild_bundle_initialize()

# --------------------------------------------------------------------------------------------------

  ######################################
  #                                    #
  # BEING AUTOMATIC GENERATION SECTION #
  #                                    #
  ######################################

# Build bundle source code.
if(BUILD_GDASBUNDLE)

  # Add JEDI packages to the bundle
  if (BUILD_JEDI)
    
    # jedicmake
    ecbuild_bundle(PROJECT jedicmake SOURCE "../sorc/jedicmake")
    include( jedicmake/cmake/Functions/git_functions.cmake )
    
    # eckit
    option("BUNDLE_SKIP_ECKIT" "Don't build eckit" "ON" )
    ecbuild_bundle(PROJECT eckit GIT "https://github.com/ecmwf/eckit.git" TAG 1.16.0 )
    
    # fckit
    option("BUNDLE_SKIP_FCKIT" "Don't build fckit" "ON" )
    ecbuild_bundle(PROJECT fckit GIT "https://github.com/ecmwf/fckit.git" TAG 0.9.2 )
    
    # atlas
    option("BUNDLE_SKIP_ATLAS" "Don't build atlas" "ON" )
    ecbuild_bundle(PROJECT atlas GIT "https://github.com/ecmwf/atlas.git" TAG 0.35.0 )
    
    # oops
    option( ENABLE_LORENZ95_MODEL "Build LORENZ95 toy model" OFF )
    option( ENABLE_QG_MODEL "Build QG toy model" OFF )
    ecbuild_bundle(PROJECT oops SOURCE "../sorc/oops")
    
    # ioda
    option(ENABLE_IODA_DATA "Obtain ioda test data from ioda-data repository (vs tarball)" ON)
    ecbuild_bundle(PROJECT ioda SOURCE "../sorc/ioda")
    
    # iodaconv
    ecbuild_bundle(PROJECT iodaconv SOURCE "../sorc/iodaconv")
    
    # crtm
    ecbuild_bundle(PROJECT crtm SOURCE "../sorc/crtm")
    
    # ufo
    option(ENABLE_UFO_DATA "Obtain ufo test data from ufo-data repository (vs tarball)" ON)
    ecbuild_bundle(PROJECT ufo SOURCE "../sorc/ufo")
    
    # gsibec
    option(BUILD_GSIBEC "Build GSI-B" OFF)
    ecbuild_bundle(PROJECT gsibec SOURCE "../sorc/gsibec")
    
    # saber
    ecbuild_bundle(PROJECT saber SOURCE "../sorc/saber")
    
    # vader
    ecbuild_bundle(PROJECT vader SOURCE "../sorc/vader")
    
    # femps
    ecbuild_bundle(PROJECT femps SOURCE "../sorc/femps")
    
    # gsw
    ecbuild_bundle(PROJECT gsw SOURCE "../sorc/gsw")
    
    # icepack
    set(BUILD_ICEPACK "ON" CACHE STRING "Build the icepack library")
    ecbuild_bundle(PROJECT icepack SOURCE "../sorc/icepack")
    
    # land-imsproc
    ecbuild_bundle(PROJECT land-imsproc SOURCE "../sorc/land-imsproc")
    
    # land-jediincr
    ecbuild_bundle(PROJECT land-jediincr SOURCE "../sorc/land-jediincr")
    
    # fms
    ecbuild_bundle(PROJECT fms SOURCE "../sorc/fms")
    
    # fv3
    ecbuild_bundle(PROJECT fv3 SOURCE "../sorc/fv3")
    
    # fv3-jedi-lm
    ecbuild_bundle(PROJECT fv3-jedi-lm SOURCE "../sorc/fv3-jedi-lm")
    
    # fv3-jedi
    option(ENABLE_FV3_JEDI_DATA "Obtain fv3-jedi test data from fv3-jedi-data repository (vs tarball)" ON)
    ecbuild_bundle(PROJECT fv3-jedi SOURCE "../sorc/fv3-jedi")
    
    # mom6
    ecbuild_bundle(PROJECT mom6 SOURCE "../sorc/mom6")
    
    # soca
    ecbuild_bundle(PROJECT soca SOURCE "../sorc/soca")
    
  endif (BUILD_JEDI)

  # Add GDAS-JEDI packages to the bundle
  if (BUILD_GDAS_JEDI)
    
    # gdas-utils
    ecbuild_bundle( PROJECT gdas-utils SOURCE "../utils")
    
    # gdas
    ecbuild_bundle( PROJECT gdas SOURCE "../")
    
  endif (BUILD_GDAS_JEDI)

  endif (BUILD_GDASBUNDLE)

  ####################################
  #                                  #
  # END AUTOMATIC GENERATION SECTION #
  #                                  #
  ####################################

  # --------------------------------------------------------------------------------------------------

  # Clone test data
  #----------------
  option(CLONE_JCSDADATA "Clone JCSDA test data repositories" OFF)
  if(CLONE_JCSDADATA)
    set(JCSDA_DATA_ROOT "$ENV{GDASAPP_TESTDATA}/jcsda")
    ecbuild_bundle( PROJECT ioda-data SOURCE "${JCSDA_DATA_ROOT}/ioda-data" )
    ecbuild_bundle( PROJECT ufo-data SOURCE "${JCSDA_DATA_ROOT}/ufo-data" )
    ecbuild_bundle( PROJECT fv3-jedi-data SOURCE "${JCSDA_DATA_ROOT}/fv3-jedi-data" )
  endif(CLONE_JCSDADATA)

endif(BUILD_GDASBUNDLE)

# Finalize bundle
# ---------------
ecbuild_bundle_finalize()