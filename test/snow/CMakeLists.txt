# test for creating pseudo ensemble for use in letkfoi
add_test(NAME test_gdasapp_snow_create_ens
         COMMAND ${PROJECT_SOURCE_DIR}/test/snow/create_bkg_ens.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/snow/)
set_tests_properties(test_gdasapp_snow_create_ens
    PROPERTIES
    ENVIRONMENT "GDASAPP_TESTDATA=$ENV{GDASAPP_TESTDATA}")

# test for preprocessing IMS snow cover data
add_test(NAME test_gdasapp_snow_imsproc
         COMMAND ${PROJECT_SOURCE_DIR}/test/snow/test_imsproc.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/snow/)
set_tests_properties(test_gdasapp_snow_imsproc
    PROPERTIES
    ENVIRONMENT "GDASAPP_TESTDATA=$ENV{GDASAPP_TESTDATA};Python3_VERSION_MAJOR=${Python3_VERSION_MAJOR};Python3_VERSION_MINOR=${Python3_VERSION_MINOR}")

# test for adding jedi increment
add_test(NAME test_gdasapp_snow_apply_jediincr
         COMMAND ${PROJECT_SOURCE_DIR}/test/snow/apply_jedi_incr.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/snow/)
set_tests_properties(test_gdasapp_snow_apply_jediincr
    PROPERTIES
    ENVIRONMENT "GDASAPP_TESTDATA=$ENV{GDASAPP_TESTDATA}")

# test for running letkfoi to assimilate snow DA
add_test(NAME test_gdasapp_snow_letkfoi_snowda
         COMMAND ${PROJECT_SOURCE_DIR}/test/snow/letkfoi_snowda.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/snow/)
set_tests_properties(test_gdasapp_snow_letkfoi_snowda
    PROPERTIES
    ENVIRONMENT "GDASAPP_TESTDATA=$ENV{GDASAPP_TESTDATA}")

# Test convert BUFR to IODA
add_test(NAME test_gdasapp_convert_bufr_adpsfc_snow
         COMMAND ${PROJECT_SOURCE_DIR}/test/snow/test_bufr2ioda.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR} ${CMAKE_BINARY_DIR} bufr_adpsfc_snow
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

