if(BUILD_GDASBUNDLE)

# jedi-cmake
  ecbuild_bundle( PROJECT jedicmake SOURCE "./jedicmake" )
  include( sorc/jedicmake/cmake/Functions/git_functions.cmake )

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
    ecbuild_bundle( PROJECT gsibec SOURCE "./gsibec" )
  endif()

# Gibbs seawater
  ecbuild_bundle( PROJECT gsw SOURCE "./gsw" )

# Core JEDI repositories
  ecbuild_bundle( PROJECT oops SOURCE "./oops" )
  ecbuild_bundle( PROJECT vader SOURCE "./vader" )
  ecbuild_bundle( PROJECT saber SOURCE "./saber" )
  option(ENABLE_IODA_DATA "Obtain ioda test data from ioda-data repository (vs tarball)" ON)
  ecbuild_bundle( PROJECT ioda SOURCE "./ioda" )
  option(ENABLE_UFO_DATA "Obtain ufo test data from ufo-data repository (vs tarball)" ON)
  ecbuild_bundle( PROJECT ufo SOURCE "./ufo" )

# FMS and FV3 dynamical core
  ecbuild_bundle( PROJECT fms GIT "https://github.com/jcsda/FMS.git" BRANCH release-stable )
  ecbuild_bundle( PROJECT fv3 SOURCE "./fv3" )

# fv3-jedi and associated repositories
  ecbuild_bundle( PROJECT femps SOURCE "./femps" )
  ecbuild_bundle( PROJECT fv3-jedi-lm SOURCE "./fv3-jedi-lm" )
  option(ENABLE_FV3_JEDI_DATA "Obtain fv3-jedi test data from fv3-jedi-data repository (vs tarball)" ON)
  ecbuild_bundle( PROJECT fv3-jedi SOURCE "./fv3-jedi" )

# SOCA associated repositories
# TODO: Move the Icepack fork to EMC github
  set(BUILD_ICEPACK "ON" CACHE STRING "Build the icepack library")
  if ( BUILD_ICEPACK )
    ecbuild_bundle( PROJECT icepack SOURCE "./icepack" )
  endif()
  ecbuild_bundle( PROJECT mom6 SOURCE "./mom6" )
  ecbuild_bundle( PROJECT soca SOURCE "./soca" )

  # Build JEDI/DA or other peripherals
  ecbuild_bundle( PROJECT gdas-utils SOURCE "./utils" )

# Build IODA converters
  option(BUILD_IODA_CONVERTERS "Build IODA Converters" ON)
  if(BUILD_IODA_CONVERTERS)
    ecbuild_bundle( PROJECT iodaconv SOURCE "./iodaconv" )
  endif()

# Land associated repositories
  ecbuild_bundle( PROJECT land-imsproc SOURCE "./land-imsproc" )
  ecbuild_bundle( PROJECT land-jediincr SOURCE "./land-jediincr" )

endif(BUILD_GDASBUNDLE)
