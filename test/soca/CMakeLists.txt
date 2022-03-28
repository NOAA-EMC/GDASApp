# Get marine observations from soca.
# ----------------------------------
set( soca_obs
  Data/Obs/adt.nc
  Data/Obs/icec.nc
  Data/Obs/icefb.nc
  Data/Obs/prof.nc
  Data/Obs/sss.nc
  Data/Obs/sst.nc
)

# Symlink observations
# --------------------
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obs)
foreach(FILENAME ${soca_obs})
  get_filename_component(filename ${FILENAME} NAME )
  execute_process( COMMAND ${CMAKE_COMMAND} -E create_symlink
           ${PROJECT_SOURCE_DIR}/soca/test/${FILENAME}
           ${CMAKE_CURRENT_BINARY_DIR}/obs/${filename} )
endforeach(FILENAME)

# Create a test R2D2 database
# ---------------------------
add_test(
      NAME    test_gdasapp_soca_obsdb
      COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/test/soca/create_obsdb.py
      WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obs
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
