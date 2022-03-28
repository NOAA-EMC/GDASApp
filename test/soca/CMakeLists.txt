# Create a test R2D2 database
# ---------------------------
set( OBS_DIR ${PROJECT_BINARY_DIR}/test/testdata )
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obs)
ecbuild_add_test(
      TARGET    test_gdasapp_soca_obsdb
      TYPE      SCRIPT
      COMMAND   ${Python3_EXECUTABLE}
      ARGS      ${PROJECT_SOURCE_DIR}/test/soca/create_obsdb.py
      WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obs
      ENVIRONMENT
        OBS_DIR=${OBS_DIR}
)

# Set runtime environement variables
# ----------------------------------
set( CDATE 2018-04-15T12:00Z ) # Analysis time TODO: check format
set( assim_freq 6 )            # DA window
set( OBS_LIST "adt_j3 sst_noaa19_l3u icec_EMC icefb_GDR temp_profile_fnmoc salt_profile_fnmoc" )
set( COMOUT ${CMAKE_CURRENT_BINARY_DIR}/3dvar )
set( COMIN_OBS ${CMAKE_CURRENT_BINARY_DIR}/obs/r2d2-shared )
set( CASE "CASE" )

# Create a working directory for prep/run/post
# --------------------------------------------
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/3dvar)

# Prep
ecbuild_add_test(
      TARGET    test_gdasapp_soca_ana_prep
      TYPE      SCRIPT
      COMMAND   ${Python3_EXECUTABLE}
      ARGS      ${PROJECT_SOURCE_DIR}/scripts/exgdas_global_marine_analysis_prep.py
      WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/3dvar
      ENVIRONMENT
        COMOUT=${COMOUT}
        COMIN_OBS=${COMIN_OBS}
)
