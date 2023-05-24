# Copy the bkg files
# ------------------
set( TESTDATA ${PROJECT_BINARY_DIR}/test/testdata )

# link input file from iodaconv to test directory
# test convert BUFR to IODA

add_test(NAME test_gdasapp_convert_bufr_temp_dbuoy
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_bufr2ioda.sh ${PROJECT_BINARY_DIR} temp_bufr_dbuoyprof
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

add_test(NAME test_gdasapp_convert_bufr_salt_dbuoy
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_bufr2ioda.sh ${PROJECT_BINARY_DIR} salt_bufr_dbuoyprof
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

add_test(NAME test_gdasapp_convert_bufr_temp_mbuoyb
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_bufr2ioda.sh ${PROJECT_BINARY_DIR} temp_bufr_mbuoybprof
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

add_test(NAME test_gdasapp_convert_bufr_salt_mbuoyb
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_bufr2ioda.sh ${PROJECT_BINARY_DIR} salt_bufr_mbuoybprof
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

add_test(NAME test_gdasapp_convert_bufr_tesacprof
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_bufr2ioda.sh ${PROJECT_BINARY_DIR} bufr_tesacprof
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

add_test(NAME test_gdasapp_convert_bufr_trkobprof
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_bufr2ioda.sh ${PROJECT_BINARY_DIR} bufr_trkobprof
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

add_test(NAME test_gdasapp_convert_bufr_sfcships
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_bufr2ioda.sh ${PROJECT_BINARY_DIR} bufr_sfcships
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

add_test(NAME test_gdasapp_convert_bufr_sfcshipsu
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_bufr2ioda.sh ${PROJECT_BINARY_DIR} bufr_sfcshipsu
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

# Symlink test input yaml files
# -----------------------------
# create testinput dir
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/testinput)

# list of test input files to install
list(APPEND test_input
  ${PROJECT_SOURCE_DIR}/parm/soca/obs/obs_list.yaml
  ${PROJECT_SOURCE_DIR}/test/soca/testinput/dumy.yaml
  )

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

# Create a test R2D2 database for obs
# -----------------------------------
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/obs)
set( OBS_DIR ${PROJECT_BINARY_DIR}/test/testdata )
add_test(NAME test_gdasapp_soca_obsdb
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/create_obsdb.py
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/obs/)
set_tests_properties(test_gdasapp_soca_obsdb
    PROPERTIES
    ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:${PROJECT_SOURCE_DIR}/../../ush/python/pygw/src:$ENV{PYTHONPATH};SOCA_TEST_OBS=${PROJECT_SOURCE_DIR}/test/soca/testdata")

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
