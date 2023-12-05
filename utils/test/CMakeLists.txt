# Create Data directory for test input config and symlink all files
list( APPEND utils_test_input
  testinput/gdas_meanioda.yaml
  testinput/gdas_rads2ioda.yaml
  testinput/gdas_ghrsst2ioda.yaml
  testinput/gdas_smap2ioda.yaml
  testinput/gdas_smos2ioda.yaml
  testinput/gdas_icecamsr2ioda.yaml
)

set( gdas_utils_test_ref
  testref/ghrsst2ioda.test
  testref/rads2ioda.test
  testref/smap2ioda.test
  testref/smos2ioda.test
  testref/icecamsr2ioda.test
)

file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/testinput)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/testrun)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc/testref)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc/testoutput)

CREATE_SYMLINK( ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR}/obsproc ${gdas_utils_test_ref} )
CREATE_SYMLINK( ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR} ${utils_test_input} )

# copy the cpp linter script
execute_process( COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_CURRENT_SOURCE_DIR}/cpplint.py ${CMAKE_BINARY_DIR}/bin/${PROJECT_NAME}_cpplint.py)

# add linter for the utils
ecbuild_add_test( TARGET test_gdasapp_util_coding_norms
                  TYPE SCRIPT
                  COMMAND ${CMAKE_BINARY_DIR}/bin/${PROJECT_NAME}_cpplint.py
                  ARGS --quiet --recursive ${CMAKE_CURRENT_SOURCE_DIR}/../
                  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/bin )

# Test example IODA utility that computes the mean of a variable
ecbuild_add_test( TARGET  test_gdasapp_util_ioda_example
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_meanioda.x
                  ARGS    "testinput/gdas_meanioda.yaml"
                  LIBS    gdas-utils)

# Prepare data for the IODA converters
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)
ecbuild_add_test( TARGET  test_gdasapp_util_prepdata
                  COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/../../utils/test/prepdata.sh
                  ARGS    ${CMAKE_CURRENT_SOURCE_DIR}/../../utils/test
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)

# Test the RADS to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_rads2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_rads2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)

# Test the GHRSST to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_ghrsst2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_ghrsst2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)

# Test the SMAP to IODA converter
# TODO(Mindo): Turn back on when date is fixed
#ecbuild_add_test( TARGET  test_gdasapp_util_smap2ioda
#                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
#                  ARGS    "../testinput/gdas_smap2ioda.yaml"
#                  LIBS    gdas-utils
#                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)

# Test the SMOS to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_smos2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_smos2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)

# Test the AMSR2 to IODA converter
# TODO(Mindo): Turn back on when date is fixed
#ecbuild_add_test( TARGET  test_gdasapp_util_icecamsr2ioda
#                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
#                  ARGS    "../testinput/gdas_icecamsr2ioda.yaml"
#                  LIBS    gdas-utils
#                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)
