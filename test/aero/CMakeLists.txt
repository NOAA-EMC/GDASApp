# tests that can run without needing all JEDI components

# test to generate YAML for aerosol 3DVar.
if (WORKFLOW_TESTS)
  add_test(NAME test_gdasapp_aero_gen_3dvar_yaml
           COMMAND ${PROJECT_SOURCE_DIR}/test/aero/genyaml_3dvar.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
           WORKING DIRECTORY ${PROJECT_BINARY_DIR}/test/testrun/)
endif()
       
# tests that require the full build
if(BUILD_GDASBUNDLE)
    # Test exgdas scripts from the global-worflow
    #if (WORKFLOW_TESTS)
    #    add_subdirectory(global-workflow)
    #endif()
endif(BUILD_GDASBUNDLE)


