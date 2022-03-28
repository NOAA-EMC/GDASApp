# tests that can run without needing all JEDI components

# tests that require the full build
if(BUILD_GDASBUNDLE)

  # link input file from iodaconv to test directory
  file(COPY ${PROJECT_SOURCE_DIR}/iodaconv/test/testinput/gdas.t06z.adpsfc.tm00.bufr_d ${PROJECT_BINARY_DIR}/test/testdata/gdas.t06z.adpsfc.tm00.bufr_d) 
  # test convert BUFR to IODA
  add_test(NAME test_gdasapp_convert_bufr_adpsfc
           COMMAND ${PROJECT_BINARY_DIR}/bin/bufr2ioda.x ${PROJECT_BINARY_DIR}/test/testinput/bufr_adpsfc.yaml
           WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

endif(BUILD_GDASBUNDLE)
