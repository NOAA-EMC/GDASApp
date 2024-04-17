# Copy the bkg files
# ------------------
set( TESTDATA ${PROJECT_BINARY_DIR}/test/testdata )

# Symlink test input yaml files
# -----------------------------
# create testinput dir
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/testinput)

# symlink
foreach(FILENAME ${test_input})
  get_filename_component(filename ${FILENAME} NAME )
  execute_process( COMMAND ${CMAKE_COMMAND} -E create_symlink
         ${FILENAME}
         ${PROJECT_BINARY_DIR}/test/soca/testinput/${filename} )
endforeach(FILENAME)

# install
install(FILES ${test_input}
        DESTINATION "test/testinput/")

# Test exgdas scripts from the global-worflow
if (WORKFLOW_TESTS)
  add_subdirectory(gw)
endif()

# test for ush/socaincr2mom6.py
add_test(NAME test_gdasapp_soca_nsst_increment_to_mom6
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/socaincr2mom6.sh ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca)
set_tests_properties(
        test_gdasapp_soca_nsst_increment_to_mom6
PROPERTIES
ENVIRONMENT "data=${TESTDATA};PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH}")
