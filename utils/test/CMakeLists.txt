# Test example IODA utility that computes the mean of a variable
ecbuild_add_test( TARGET  test_gdasapp_util_ioda_example
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_meanioda.x
                  ARGS    "testinput/gdas_meanioda.yaml"
                  LIBS    gdas-utils)