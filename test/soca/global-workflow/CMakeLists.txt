# test for creating an experiment directory within the global-workflow
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/global-workflow/testrun)

add_test(NAME test_gdasapp_setup_soca_cycled_exp
  COMMAND ${PROJECT_SOURCE_DIR}/test/soca/global-workflow/setup_workflow_exp.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/global-workflow/testrun)

add_test(NAME test_gdasapp_soca_jjob_soca_prep
  COMMAND ${PROJECT_SOURCE_DIR}/test/soca/global-workflow/jjob_prep.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/global-workflow/testrun)

add_test(NAME test_gdasapp_soca_jjob_soca_run
  COMMAND ${PROJECT_SOURCE_DIR}/test/soca/global-workflow/jjob_run.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/global-workflow/testrun)
