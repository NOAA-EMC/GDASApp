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

# Copy the bkg files
# ------------------
set( TESTDATA ${PROJECT_BINARY_DIR}/test/testdata )
file(GLOB bkg_diag "${TESTDATA}/ocn_da_2018_04_15_*.nc")
list(APPEND bkg_diag "${TESTDATA}/MOM.res.nc")
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/bkg/RESTART)
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/bkg/RESTART_GES)
file(COPY ${bkg_diag} DESTINATION ${PROJECT_BINARY_DIR}/test/soca/bkg/RESTART)

foreach(FILENAME ${test_input})
  get_filename_component(filename ${FILENAME} NAME )
  execute_process( COMMAND ${CMAKE_COMMAND} -E create_symlink
         ${FILENAME}
         ${PROJECT_BINARY_DIR}/test/soca/testinput/${filename} )
endforeach(FILENAME)


# tests below require the full build
if(BUILD_GDASBUNDLE)

  # link input file from iodaconv to test directory
  file(CREATE_LINK ${PROJECT_SOURCE_DIR}/iodaconv/test/testinput/dbuoy_20180415_bufr ${PROJECT_BINARY_DIR}/test/testdata/dbuoy_20180415_bufr SYMBOLIC)
  # test convert BUFR to IODA
  add_test(NAME test_gdasapp_convert_bufr_dbuoy
           COMMAND ${PROJECT_BINARY_DIR}/bin/bufr2ioda.x ${PROJECT_BINARY_DIR}/test/testinput/bufr_dbuoy.yaml
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

  # Test exgdas_global_marine_analysis_prep.py
  # ------------------------------------------
  file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/3dvar)

  # Prep
  add_test(NAME test_gdasapp_soca_ana_prep
           COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_prep.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
           WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/3dvar)
  set_tests_properties(test_gdasapp_soca_ana_prep
        PROPERTIES
            ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH}")

  # Test exgdas_global_marine_analysis_run.sh
  # -----------------------------------------
  add_test(NAME test_gdasapp_soca_ana_run
           COMMAND ${PROJECT_SOURCE_DIR}/test/soca/test_run.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
           WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/3dvar/analysis)
  set_tests_properties(test_gdasapp_soca_ana_run
        PROPERTIES
            DEPENDS "test_gdasapp_soca_ana_prep"
            ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH}")
endif(BUILD_GDASBUNDLE)
