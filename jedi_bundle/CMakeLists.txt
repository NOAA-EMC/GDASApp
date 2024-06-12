# JEDI Bundle For GDASapp
# -----------------------

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


# Initialize bundle
# -----------------
ecbuild_bundle_initialize()

# --------------------------------------------------------------------------------------------------

macro(add_package_to_bundle PROJECT_NAME PACKAGE_NAME LOCATION URL MIN_REQUIRED_VERSION )

  # This macro finds dependencies and checks that they are either not present at all (not found)
  # or whether a minimum required version is satisfied. If the package is found but the version
  # is too old, the build will be stopped. If the package is not found, a message will be issued
  # but the build will continue without it.

  # Building with a package that is too old will not work. And having it in the path will likely
  # cause problems if a sufficiently new version is built anyway. But we also want to continue
  # if the package is not found at all because we can add it to the bundle and build locally.

  # If path ${CMAKE_BINARY_DIR}/PROJECT_NAME does not exist then look for the package.
  # This is needed because sometimes CMake is re-triggered and this results in packages that are
  # being built in the bundle as being found, when the following logic assumes they are not.
  if (NOT EXISTS "${CMAKE_BINARY_DIR}/${PROJECT_NAME}")

  # First try to find the pacakge, do so silenty and do not abort if not found
    find_package(${PACKAGE_NAME} QUIET)

    # Check if the package is found and if the version is sufficient
    string(APPEND message "Assessing whether to add project '${PROJECT_NAME}' to the bundle ... ")
    if (NOT ${PACKAGE_NAME}_FOUND)
      string(APPEND message "${PROJECT_NAME} not found so will be built with the bundle")
      message(STATUS "${message}")
    else()
      if (${PACKAGE_NAME}_VERSION VERSION_LESS ${MIN_REQUIRED_VERSION})
        string(APPEND message "${PROJECT_NAME} found but the version is too old. Found version ")
        string(APPEND message "${${PACKAGE_NAME}_VERSION}. Minimum required version is ")
        string(APPEND message "${MIN_REQUIRED_VERSION}. Adding this package to the bundle will ")
        string(APPEND message "likely lead to conflicts and build/runtime errors. Ensure this ")
        string(APPEND message "version of the package is not in the path before continuing.")
        message(FATAL_ERROR "${message}")
      else()

        # Find the package again with the minimum required version and make it required
        # This is not technically required but it prevents the package being listed as optional
        # at the end of the cmake step, which could otherwise be misleading.
        find_package(${PACKAGE_NAME} ${MIN_REQUIRED_VERSION} REQUIRED QUIET)

        string(APPEND message "${PROJECT_NAME} found and the version is ")
        string(APPEND message "${${PACKAGE_NAME}_VERSION}. Package not added to bundle.")
        message(STATUS "${message}")
      endif()
    endif()

    # Remove global message variable
    unset(message)

  endif()

  # If the package is not found at all then add it to the bundle
  # This might include some pre- and post-amble to the bundle line, which is added via templating.
  if (NOT ${PACKAGE_NAME}_FOUND)

    # Unset the package found flag. This is required because the package is not found and otherwise
    # it makes ecbuild think the package is setting the flag manually, which would not be permitted.
    unset(${PACKAGE_NAME}_FOUND)

    ############# BEGIN AUTOGENERATION SECTION #############
    # If PRE_INCLUDE is not an empty string then put it here
    if (${PROJECT_NAME} STREQUAL "oops")
      option( ENABLE_LORENZ95_MODEL "Build LORENZ95 toy model" OFF )
      option( ENABLE_QG_MODEL "Build QG toy model" OFF )
    endif()
    if (${PROJECT_NAME} STREQUAL "ioda")
      option(ENABLE_IODA_DATA "Obtain ioda test data from ioda-data repository (vs tarball)" ON)
    endif()
    if (${PROJECT_NAME} STREQUAL "ufo")
      option(ENABLE_UFO_DATA "Obtain ufo test data from ufo-data repository (vs tarball)" ON)
    endif()
    if (${PROJECT_NAME} STREQUAL "gsibec")
      option(BUILD_GSIBEC "Build GSI-B" OFF)
    endif()
    if (${PROJECT_NAME} STREQUAL "icepack")
      set(BUILD_ICEPACK "ON" CACHE STRING "Build the icepack library")
    endif()
    if (${PROJECT_NAME} STREQUAL "fv3-jedi")
      option(ENABLE_FV3_JEDI_DATA "Obtain fv3-jedi test data from fv3-jedi-data repository (vs tarball)" ON)
    endif()
    ############## END AUTOGENERATION SECTION ##############

    # Based on the location (GIT or SOURCE) add the package to the bundle
    if (${LOCATION} STREQUAL "GIT")
      ecbuild_bundle( PROJECT ${PROJECT_NAME} GIT ${URL} TAG ${MIN_REQUIRED_VERSION} )
    elseif (${LOCATION} STREQUAL "SOURCE")
      ecbuild_bundle( PROJECT ${PROJECT_NAME} SOURCE ${URL} )
    else()
      message(FATAL_ERROR "Unknown location type '${LOCATION}'")
    endif()

    ############# BEGIN AUTOGENERATION SECTION #############
    # If POST_INCLUDE is not an empty string then put it here
    if (${PROJECT_NAME} STREQUAL "jedicmake")
      include( jedicmake/cmake/Functions/git_functions.cmake )
    endif()
    ############## END AUTOGENERATION SECTION ##############

  endif()

endmacro()

# --------------------------------------------------------------------------------------------------

######################################
#                                    #
# THE BELOW SECTION IS AUTOMATICALLY #
# GENERATED FROM gdas_bundle.yaml    #
# AND BY RUNNING:                    #
# python3 generate_bundle.py         #
#                                    #
# DO NOT EDIT MANUALLY!              #
#                                    #
######################################


# Add all the packages to the bundle (if needed)
# ----------------------------------------------

# jedicmake
add_package_to_bundle(jedicmake jedicmake SOURCE "../sorc/jedicmake" 1.4.0)

# eckit
add_package_to_bundle(eckit eckit GIT "https://github.com/ecmwf/eckit.git" 1.16.0)

# fckit
add_package_to_bundle(fckit fckit GIT "https://github.com/ecmwf/fckit.git" 0.9.2)

# atlas
add_package_to_bundle(atlas atlas GIT "https://github.com/ecmwf/atlas.git" 0.35.0)

# oops
add_package_to_bundle(oops oops SOURCE "../sorc/oops" 1.10.0)

# ioda
add_package_to_bundle(ioda ioda SOURCE "../sorc/ioda" 2.9.0)

# iodaconv
add_package_to_bundle(iodaconv iodaconv SOURCE "../sorc/iodaconv" 0.0.1)

# crtm
add_package_to_bundle(crtm crtm SOURCE "../sorc/crtm" 2.4.1)

# ufo
add_package_to_bundle(ufo ufo SOURCE "../sorc/ufo" 1.10.0)

# gsibec
add_package_to_bundle(gsibec gsibec SOURCE "../sorc/gsibec" 1.2.1)

# saber
add_package_to_bundle(saber saber SOURCE "../sorc/saber" 1.10.0)

# vader
add_package_to_bundle(vader vader SOURCE "../sorc/vader" 1.7.0)

# femps
add_package_to_bundle(femps femps SOURCE "../sorc/femps" 1.3.0)

# gsw
add_package_to_bundle(gsw gsw SOURCE "../sorc/gsw" 3.0.7)

# icepack
add_package_to_bundle(icepack icepack SOURCE "../sorc/icepack" 1.2.0)

# land-imsproc
add_package_to_bundle(land-imsproc imsproc SOURCE "../sorc/land-imsproc" 2022.1)

# land-jediincr
add_package_to_bundle(land-jediincr jediincr SOURCE "../sorc/land-jediincr" 2022.1)

# fms
add_package_to_bundle(fms fms SOURCE "../sorc/fms" 2020.4.0)

# fv3
add_package_to_bundle(fv3 fv3 SOURCE "../sorc/fv3" 1.2.0)

# fv3-jedi-lm
add_package_to_bundle(fv3-jedi-lm fv3jedilm SOURCE "../sorc/fv3-jedi-lm" 1.5.0)

# fv3-jedi
add_package_to_bundle(fv3-jedi fv3jedi SOURCE "../sorc/fv3-jedi" 1.9.0)

# mom6
add_package_to_bundle(mom6 mom6 SOURCE "../sorc/mom6" 2022.1.0)

# soca
add_package_to_bundle(soca soca SOURCE "../sorc/soca" 1.8.0)

# gdas-jedi
add_package_to_bundle(gdas-jedi gdasjedi SOURCE "../sorc/gdas-jedi" 0.0.1)


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

# Install complete project
# ------------------------
ecbuild_install_project( NAME gdasjedibundle )

# Finalize bundle
# ---------------
ecbuild_bundle_finalize()
