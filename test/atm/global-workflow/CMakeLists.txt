# test for creating an experiment directory within the global-workflow
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_setup_atm_cycled_exp
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/setup_workflow_exp.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_var_init
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_var_init.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_var_run
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_var_run.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_var_inc
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_var_inc.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_var_final
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_var_final.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_ens_init
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_init.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_ens_letkf
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_letkf.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
	  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_ens_init_split
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_init_split.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_ens_obs
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_obs.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
          WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_ens_sol
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_sol.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
          WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)
	
add_test(NAME test_gdasapp_atm_jjob_ens_inc
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_inc.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

add_test(NAME test_gdasapp_atm_jjob_ens_final
  COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_final.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

