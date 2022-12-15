# test for creating pseudo ensemble for use in letkfoi
add_test(NAME test_gdasapp_land_create_ens
         COMMAND ${PROJECT_SOURCE_DIR}/test/land/create_bkg_ens.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/land/)
set_tests_properties(test_gdasapp_land_create_ens
    PROPERTIES
    ENVIRONMENT "GDASAPP_TESTDATA=$ENV{GDASAPP_TESTDATA}")

# test for preprocessing IMS snow cover data
add_test(NAME test_gdasapp_land_imsproc
         COMMAND ${PROJECT_SOURCE_DIR}/test/land/test_imsproc.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/land/)
set_tests_properties(test_gdasapp_land_imsproc
    PROPERTIES
    ENVIRONMENT "GDASAPP_TESTDATA=$ENV{GDASAPP_TESTDATA};Python3_VERSION_MAJOR=${Python3_VERSION_MAJOR};Python3_VERSION_MINOR=${Python3_VERSION_MINOR}")

# test for adding jedi increment
add_test(NAME test_gdasapp_land_apply_jediincr
         COMMAND ${PROJECT_SOURCE_DIR}/test/land/apply_jedi_incr.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/land/)
set_tests_properties(test_gdasapp_land_apply_jediincr
    PROPERTIES
    ENVIRONMENT "GDASAPP_TESTDATA=$ENV{GDASAPP_TESTDATA}")

