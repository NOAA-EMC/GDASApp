# Create a test R2D2 database for obs
# -----------------------------------
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/obs)
set( OBS_DIR ${PROJECT_BINARY_DIR}/test/testdata )
add_test(NAME test_gdasapp_soca_obsdb
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/create_obsdb.py
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/obs/)
set_tests_properties(test_gdasapp_soca_obsdb
    PROPERTIES
    ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH};OBS_DIR=${OBS_DIR}")

# Prepare backgrounds
# -------------------
# 1 - create fake 3 hourly restarts under RESTART
# 2 - store them with R2D2
set( TESTDATA ${PROJECT_BINARY_DIR}/test/testdata )
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/bkg)
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/bkg/RESTART)
add_test(NAME test_gdasapp_soca_bkgdb
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/create_bkgdb.py
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/bkg)
set_tests_properties(test_gdasapp_soca_bkgdb
    PROPERTIES
    ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH};TESTDATA=${TESTDATA}"
  )

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


# Create a working directory for prep/run/post
# --------------------------------------------
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/3dvar)

# Prep
add_test(NAME test_gdasapp_soca_ana_prep
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_prep.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/3dvar)
set_tests_properties(test_gdasapp_soca_ana_prep
      PROPERTIES
          ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH}")
