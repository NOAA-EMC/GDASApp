# test for creating an experiment directory within the global-workflow
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/testrun)

add_test(NAME test_gdasapp_setup_soca_cycled_exp
  COMMAND ${PROJECT_SOURCE_DIR}/test/soca/gw/setup_workflow_exp.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/testrun)

add_test(NAME test_gdasapp_soca_bkg2comrot
  COMMAND ${PROJECT_SOURCE_DIR}/test/soca/gw/bkg2comrot.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/testrun)
set_tests_properties(test_gdasapp_soca_bkg2comrot
  PROPERTIES
DEPENDS "test_gdasapp_soca_cycled_exp")

add_test(NAME test_gdasapp_soca_jjob_soca_prep
  COMMAND ${PROJECT_SOURCE_DIR}/test/soca/gw/jjob_prep.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/testrun)
set_tests_properties(test_gdasapp_soca_jjob_soca_prep
  PROPERTIES
    DEPENDS "test_gdasapp_soca_cycled_exp;test_gdasapp_soca_bkg2comrot")

# TODO: This test is broken on Orion, skip it for now when running the CI on Orion.
IF (IS_DIRECTORY /work2/noaa/da)
  message("Skipping this test for now")
ELSE()
  add_test(NAME test_gdasapp_soca_jjob_soca_run
    COMMAND ${PROJECT_SOURCE_DIR}/test/soca/gw/jjob_run.sh
            ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
    WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/testrun)
    set_tests_properties(test_gdasapp_soca_jjob_soca_run
    PROPERTIES
      DEPENDS "test_gdasapp_soca_cycled_exp;test_gdasapp_soca_bkg2comrot;test_gdasapp_soca_jjob_soca_prep")
ENDIF()
