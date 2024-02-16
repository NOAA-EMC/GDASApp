# tests that can run without needing all JEDI components


# tests that require the full build
if(BUILD_GDASBUNDLE)
    # Test exgdas scripts from the global-worflow
    #if (WORKFLOW_TESTS)
    #    add_subdirectory(global-workflow)
    #endif()
endif(BUILD_GDASBUNDLE)


