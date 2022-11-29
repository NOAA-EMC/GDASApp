# test for creating pseudo ensemble for use in letkfoi
add_test(NAME test_gdasapp_land_create_ens
         COMMAND ${PROJECT_SOURCE_DIR}/test/land/create_bkg_ens.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/land/)

