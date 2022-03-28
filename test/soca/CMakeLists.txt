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
