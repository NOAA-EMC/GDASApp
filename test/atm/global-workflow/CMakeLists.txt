set(COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/setup_workflow_exp.sh)
set(ARGS "${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}")
set(WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

function(add_jjob_test TARGET TEST_DEPENDS)
  message(STATUS "preparing ${TARGET} for atm_jjob ctests")
  ecbuild_add_test(TARGET ${TARGET}
                   TYPE SCRIPT
                   COMMAND ${COMMAND}
                   ARGS ${ARGS}
                   WORKING_DIRECTORY ${WORKING_DIRECTORY}
                   TEST_DEPENDS ${TEST_DEPENDS})
endfunction()

# test for creating an experiment directory within the global-workflow
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

# Setup jjob tests
ecbuild_add_test(TARGET test_gdasapp_setup_atm_cycled_exp
                 TYPE SCRIPT
                 COMMAND ${COMMAND}
                 ARGS ${ARGS}
                 WORKING_DIRECTORY ${WORKING_DIRECTORY})

# Variational jjobs
add_jjob_test(test_gdasapp_atm_jjob_var_init test_gdasapp_setup_atm_cycled_exp)
add_jjob_test(test_gdasapp_atm_jjob_var_run test_gdasapp_atm_jjob_var_init)
add_jjob_test(test_gdasapp_atm_jjob_var_inc test_gdasapp_atm_jjob_var_run)
add_jjob_test(test_gdasapp_atm_jjob_var_final test_gdasapp_atm_jjob_var_inc)

# Ensemble jjobs with no split observer-solver
add_jjob_test(test_gdasapp_atm_jjob_ens_init test_gdasapp_setup_atm_cycled_exp)
add_jjob_test(test_gdasapp_atm_jjob_ens_letkf test_gdasapp_atm_jjob_ens_init)

# Ensemble jjobs with split observer-solver
add_jjob_test(test_gdasapp_atm_jjob_ens_init_split test_gdasapp_setup_atm_cycled_exp)
add_jjob_test(test_gdasapp_atm_jjob_ens_obs test_gdasapp_atm_jjob_ens_init_split)
add_jjob_test(test_gdasapp_atm_jjob_ens_sol test_gdasapp_atm_jjob_ens_obs)
add_jjob_test(test_gdasapp_atm_jjob_ens_inc test_gdasapp_atm_jjob_ens_sol)
add_jjob_test(test_gdasapp_atm_jjob_ens_final test_gdasapp_atm_jjob_ens_inc)
