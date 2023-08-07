# Create Data directory for test input config and symlink all files
list( APPEND utils_test_input
  testinput/gdas_meanioda.yaml
)

file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/testinput)
CREATE_SYMLINK( ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR} ${utils_test_input} )

# Test example IODA utility that computes the mean of a variable
ecbuild_add_test( TARGET  test_gdasapp_util_ioda_example
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_meanioda.x
                  ARGS    "testinput/gdas_meanioda.yaml"
                  LIBS    gdas-utils)