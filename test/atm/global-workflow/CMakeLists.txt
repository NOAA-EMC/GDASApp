# test for creating an experiment directory within the global-workflow
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

ecbuild_add_test(TARGET test_gdasapp_setup_atm_jjob_cycled_exp
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/setup_workflow_exp.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun)

ecbuild_add_test(TARGET test_gdasapp_atm_jjob_var_init
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_var_init.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_setup_atm_jjob_cycled_exp)

ecbuild_add_test(TARGET test_gdasapp_atm_jjob_var_run
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_var_run.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_atm_jjob_var_init)

ecbuild_add_test(TARGET test_gdasapp_atm_jjob_var_inc
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_var_inc.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_atm_jjob_var_run)

ecbuild_add_test(TARGET test_gdasapp_atm_jjob_var_final
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_var_final.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_atm_jjob_var_inc)

ecbuild_add_test(TARGET test_gdasapp_atm_jjob_ens_init
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_init.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_setup_atm_jjob_cycled_exp)

ecbuild_add_test(TARGET test_gdasapp_atm_jjob_ens_letkf
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_letkf.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
	         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_atm_jjob_ens_init)

ecbuild_add_test(TARGET test_gdasapp_atm_jjob_ens_init_split
                 TYPE SCRIPT                 
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_init_split.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_atm_jjob_ens_letkf)

ecbuild_add_test(TARGET test_gdasapp_atm_jjob_ens_obs
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_obs.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_atm_jjob_ens_init_split)

ecbuild_add_test(TARGET test_gdasapp_atm_jjob_ens_sol
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_sol.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_atm_jjob_ens_obs)
	
ecbuild_add_test(TARGET test_gdasapp_atm_jjob_ens_inc
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_inc.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_atm_jjob_ens_sol)

ecbuild_add_test(TARGET test_gdasapp_atm_jjob_ens_final
                 TYPE SCRIPT
                 COMMAND ${PROJECT_SOURCE_DIR}/test/atm/global-workflow/jjob_ens_final.sh
                 ARGS ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                 WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/atm/global-workflow/testrun
                 TEST_DEPENDS test_gdasapp_atm_jjob_ens_inc)

