# test for creating an experiment directory within the global-workflow
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/aero/global-workflow/testrun)

# test to setup the experiment for aerosol 3DVar
add_test(NAME test_gdasapp_setup_aero_cycled_exp
  COMMAND ${PROJECT_SOURCE_DIR}/test/aero/global-workflow/setup_workflow_exp.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/aero/global-workflow/testrun)

# test to initialize the aerosol 3DVar
add_test(NAME test_gdasapp_aero_jjob_var_init
  COMMAND ${PROJECT_SOURCE_DIR}/test/aero/global-workflow/jjob_var_init.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/aero/global-workflow/testrun)

# test to run the aerosol 3DVar
add_test(NAME test_gdasapp_aero_jjob_var_run
  COMMAND ${PROJECT_SOURCE_DIR}/test/aero/global-workflow/jjob_var_run.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/aero/global-workflow/testrun)

# test to finalize the aerosol 3DVar
add_test(NAME test_gdasapp_aero_jjob_var_final
  COMMAND ${PROJECT_SOURCE_DIR}/test/aero/global-workflow/jjob_var_final.sh
          ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
  WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/aero/global-workflow/testrun)
