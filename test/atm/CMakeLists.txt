# tests that can run without needing all JEDI components

# tests that require the full build
if (BUILD_GDASBUNDLE)
  if (BUILD_IODA_CONVERTERS)
    # link input file from iodaconv to test directory
    file(CREATE_LINK ${CMAKE_SOURCE_DIR}/iodaconv/test/testinput/gdas.t06z.adpsfc.tm00.bufr_d ${PROJECT_BINARY_DIR}/test/testdata/gdas.t06z.adpsfc.tm00.bufr_d SYMBOLIC)
    # test convert BUFR to IODA
    add_test(NAME test_gdasapp_convert_bufr_adpsfc
            COMMAND ${CMAKE_BINARY_DIR}/bin/bufr2ioda.x ${PROJECT_BINARY_DIR}/test/testinput/bufr_adpsfc.yaml
            WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
  endif()

  # test generate UFO CRTM sat bias files from GSI sat bias files
  add_test(NAME test_gdasapp_convert_gsi_satbias
           COMMAND ${PROJECT_SOURCE_DIR}/test/atm/test_convert_gsi_satbias.sh ${PROJECT_SOURCE_DIR} ${PROJECT_BINARY_DIR}
           WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

# Test exgdas scripts from the global-worflow
  if (WORKFLOW_TESTS)
    add_subdirectory(global-workflow)
  endif()

  # check if we can run regression tests on this machine
  if (REGRESSION_TESTS)
    # add a test for 3DVar
    add_test(NAME test_gdasapp_regression_atm_3dvar
             COMMAND ${PROJECT_SOURCE_DIR}/test/atm/regression_test_3dvar.sh ${PROJECT_SOURCE_DIR} ${PROJECT_BINARY_DIR}
             WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
  endif()

endif(BUILD_GDASBUNDLE)
