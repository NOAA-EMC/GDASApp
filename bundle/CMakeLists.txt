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
option(CLONE_JCSDADATA "Clone JCSDA test data repositories" OFF)
option(WORKFLOW_TESTS "Include global-workflow dependent tests" OFF)

# Depend path for non-ecbuild packages
set(DEPEND_LIB_ROOT ${CMAKE_CURRENT_BINARY_DIR}/Depends)
list(APPEND CMAKE_PREFIX_PATH ${DEPEND_LIB_ROOT})

# Library path for non-ecbuild packages
link_directories(${CMAKE_CURRENT_BINARY_DIR}/lib)

include( GNUInstallDirs )
if(APPLE)
  list( APPEND CMAKE_INSTALL_RPATH $ENV{llvm_openmp_ROOT}/lib )
endif()
list( APPEND CMAKE_INSTALL_RPATH ${CMAKE_CURRENT_BINARY_DIR}/fv3 )

# Initialize bundle
# -----------------
ecbuild_bundle_initialize()

# Build bundle source code.
if(BUILD_GDASBUNDLE)

# jedi-cmake
  ecbuild_bundle( PROJECT jedicmake SOURCE "../sorc/jedicmake" )
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
  # TODO remove the CRTM from here and use it as a library
  #option("BUNDLE_SKIP_CRTM" "Don't build CRTM" "OFF") # Don't build crtm unless user passes -DBUNDLE_SKIP_CRTM=OFF
  #ecbuild_bundle( PROJECT crtm GIT "https://github.com/JCSDA/crtm.git"   TAG v2.4.1-jedi.1 )
  ecbuild_bundle( PROJECT crtm SOURCE "../sorc/crtm" )

# Build GSI-B
  option(BUILD_GSIBEC "Build GSI-B" OFF)
  if(BUILD_GSIBEC)
    ecbuild_bundle( PROJECT gsibec SOURCE "../sorc/gsibec" )
  endif()

# Gibbs seawater
  ecbuild_bundle( PROJECT gsw SOURCE "../sorc/gsw" )

# EMC BUFR-query library
  ecbuild_bundle( PROJECT bufr-query SOURCE "../sorc/bufr-query" )

# Core JEDI repositories
  ecbuild_bundle( PROJECT oops SOURCE "../sorc/oops" )
  ecbuild_bundle( PROJECT vader SOURCE "../sorc/vader" )
  ecbuild_bundle( PROJECT saber SOURCE "../sorc/saber" )
  option(ENABLE_IODA_DATA "Obtain ioda test data from ioda-data repository (vs tarball)" ON)
  ecbuild_bundle( PROJECT ioda SOURCE "../sorc/ioda" )
  option(ENABLE_UFO_DATA "Obtain ufo test data from ufo-data repository (vs tarball)" ON)
  ecbuild_bundle( PROJECT ufo SOURCE "../sorc/ufo" )

# FV3 dynamical core
  include(fv3-interface.cmake)
  ecbuild_bundle( PROJECT fv3 SOURCE "../sorc/fv3" )

# fv3-jedi and associated repositories
  ecbuild_bundle( PROJECT femps SOURCE "../sorc/femps" )
  ecbuild_bundle( PROJECT fv3-jedi-lm SOURCE "../sorc/fv3-jedi-lm" )
  option(ENABLE_FV3_JEDI_DATA "Obtain fv3-jedi test data from fv3-jedi-data repository (vs tarball)" ON)
  ecbuild_bundle( PROJECT fv3-jedi SOURCE "../sorc/fv3-jedi" )

# SOCA associated repositories
  ecbuild_bundle( PROJECT soca SOURCE "../sorc/soca" )

  # Build JEDI/DA or other peripherals
  ecbuild_bundle( PROJECT gdas-utils SOURCE "../utils" )
  ecbuild_bundle( PROJECT da-utils SOURCE "../sorc/da-utils" )

# Build IODA converters
  option(BUILD_IODA_CONVERTERS "Build IODA Converters" ON)
  if(BUILD_IODA_CONVERTERS)
    ecbuild_bundle( PROJECT iodaconv SOURCE "../sorc/iodaconv" )
  endif()

# Land associated repositories
  ecbuild_bundle( PROJECT land-imsproc SOURCE "../sorc/land-imsproc" )
  ecbuild_bundle( PROJECT land-jediincr SOURCE "../sorc/land-jediincr" )

# GDASApp
  ecbuild_bundle( PROJECT gdas SOURCE "../")

# ioda, ufo, fv3-jedi, and saber test data
#---------------------------------
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
