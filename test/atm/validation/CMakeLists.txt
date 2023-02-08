# test for creating a working directory for validation testing
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/validation/testrun)

#----------------------------
# GDAS UFO Validation tests
#----------------------------
# everyone can run the geoval validation tests if they wish
add_test(NAME test_gdasapp_ufo_geovals_validation
COMMAND ${PROJECT_SOURCE_DIR}/test/atm/validation/test_ufo_geovals_validation.sh ${PROJECT_SOURCE_DIR} ${PROJECT_BINARY_DIR}
WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/validation/testrun)

# only run the HTML generation/upload if we are running as CI
if(DEFINED ENV{GDAS_CI_HOST})
  add_test(NAME test_gdasapp_summary_ufo_geovals_validation
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/validation/summary_ufo_geovals_validation.sh ${PROJECT_SOURCE_DIR} ${PROJECT_BINARY_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/validation/testrun)
endif()