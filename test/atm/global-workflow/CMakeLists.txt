# test for creating an experiment directory within the global-workflow
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_setup_atm_cycled_exp
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/setup_workflow_exp.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_atm_prep
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_prep.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_atm_run
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_run.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_atm_post
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_post.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_ens_prep
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_prep.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_ens_run
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_run.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_ens_post
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_post.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)
