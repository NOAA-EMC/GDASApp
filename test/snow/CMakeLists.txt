# test for creating pseudo ensemble for use in letkfoi
add_test(NAME test_gdasapp_snow_create_ens
         COMMAND ${PROJECT_SOURCE_DIR}/test/snow/create_bkg_ens.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/snow/)
set_tests_properties(test_gdasapp_snow_create_ens
    PROPERTIES
    ENVIRONMENT "GDASAPP_TESTDATA=$ENV{GDASAPP_TESTDATA}")

if (BUILD_IODA_CONVERTERS)
# test for preprocessing IMS snow cover data
add_test(NAME test_gdasapp_snow_imsproc
         COMMAND ${PROJECT_SOURCE_DIR}/test/snow/test_imsproc.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/snow/)
set_tests_properties(test_gdasapp_snow_imsproc
    PROPERTIES
    ENVIRONMENT "GDASAPP_TESTDATA=$ENV{GDASAPP_TESTDATA};Python3_VERSION_MAJOR=${Python3_VERSION_MAJOR};Python3_VERSION_MINOR=${Python3_VERSION_MINOR}")
endif()

# test for adding jedi increment
#add_test(NAME test_gdasapp_snow_apply_jediincr
#         COMMAND ${PROJECT_SOURCE_DIR}/test/snow/apply_jedi_incr.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
#         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/snow/)
#set_tests_properties(test_gdasapp_snow_apply_jediincr
#    PROPERTIES
#    ENVIRONMENT "GDASAPP_TESTDATA=$ENV{GDASAPP_TESTDATA}")

if (BUILD_IODA_CONVERTERS)
# Test convert BUFR to IODA
add_test(NAME test_gdasapp_convert_bufr_adpsfc_snow
         COMMAND ${PROJECT_SOURCE_DIR}/test/snow/test_bufr2ioda.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR} ${CMAKE_BINARY_DIR} bufr_adpsfc_snow
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
endif()
