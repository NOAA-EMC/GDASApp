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
set( WRK_DIR ${CMAKE_CURRENT_BINARY_DIR}/obs )
ecbuild_add_test(
      TARGET    test_gdasapp_soca_obsdb
      TYPE      SCRIPT
      COMMAND   ${Python3_EXECUTABLE}
      ARGS      ${PROJECT_SOURCE_DIR}/test/soca/create_obsdb.py
      WORKING_DIRECTORY ${WRK_DIR}
      ENVIRONMENT
        WRK_DIR=${WRK_DIR}
)
