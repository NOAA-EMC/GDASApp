# tests that can run without needing all JEDI components

# tests that require the full build
if (BUILD_GDASBUNDLE)

  # link input file from iodaconv to test directory
  file(CREATE_LINK ${CMAKE_SOURCE_DIR}/iodaconv/test/testinput/gdas.t06z.adpsfc.tm00.bufr_d ${PROJECT_BINARY_DIR}/test/testdata/gdas.t06z.adpsfc.tm00.bufr_d SYMBOLIC)
  # test convert BUFR to IODA
  add_test(NAME test_gdasapp_convert_bufr_adpsfc
           COMMAND ${CMAKE_BINARY_DIR}/bin/bufr2ioda.x ${PROJECT_BINARY_DIR}/test/testinput/bufr_adpsfc.yaml
           WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

  # test generate UFO CRTM sat bias files from GSI sat bias files
  add_test(NAME test_gdasapp_convert_gsi_satbias
           COMMAND ${PROJECT_SOURCE_DIR}/test/atm/test_convert_gsi_satbias.sh ${PROJECT_SOURCE_DIR} ${PROJECT_BINARY_DIR}
           WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

  # test saving the output of the previous test to an R2D2 database
  add_test(NAME test_gdasapp_store_gsi_satbias
           COMMAND ${PROJECT_SOURCE_DIR}/test/atm/test_store_gsi_satbias.py
           WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
  set_tests_properties(test_gdasapp_store_gsi_satbias
      PROPERTIES
          DEPENDS "test_gdasapp_convert_gsi_satbias"
          ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH}"
  )

# Test exgdas scripts from the global-worflow
  if (WORKFLOW_TESTS)
    add_subdirectory(global-workflow)
  endif()

endif(BUILD_GDASBUNDLE)
