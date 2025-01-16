##### get test data from EMC FTP server
# set URL and hash
set(URL "https://ftp.emc.ncep.noaa.gov/static_files/public/GDASApp")
set(SHA "bda76f96666405f72abef56ad4d7d5b93ca153cd7d675853fbdb199096949f8a")
string(SUBSTRING ${SHA} 0 6 SHORTSHA)
set(TAR "gdasapp-fix-${SHORTSHA}.tgz")
IF(DEFINED ENV{GDASAPP_UNIT_TEST_DATA_PATH})
  set(GDASAPP_UNIT_TEST_DATA_PATH "$ENV{GDASAPP_UNIT_TEST_DATA_PATH}")
  file(COPY ${GDASAPP_UNIT_TEST_DATA_PATH}/${TAR} DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
ELSE()
  # download test files
  file(DOWNLOAD
    ${URL}/${TAR}
    ${CMAKE_CURRENT_BINARY_DIR}/${TAR}
    INACTIVITY_TIMEOUT 30
    TIMEOUT 90
    SHOW_PROGRESS
    STATUS status
    EXPECTED_HASH SHA256=${SHA}
    )
ENDIF()
# Extract tarball.
file(ARCHIVE_EXTRACT INPUT ${CMAKE_CURRENT_BINARY_DIR}/${TAR}
  DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
# list of test binary/data files to install
list(APPEND test_data
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/adt.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/sst.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/sss.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/prof.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/icec.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/icefb.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/MOM.res.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/iced.2019-04-15-43200.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_09.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_10.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_11.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_12.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_13.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_14.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_15.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/gdas.t00z.abias
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/gdas.t00z.abias_pc
)

# install
install(FILES ${test_data}
        DESTINATION "test/testdata/")

# list of test input files to install
list(APPEND test_input
  ${PROJECT_SOURCE_DIR}/test/testinput/check_yaml_keys_ref.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/check_yaml_keys_test.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/bufr_adpsfc.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/bufr_adpsfc_snow.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/amsua_n19_ewok.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/temp_bufr_dbuoyprof.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/salt_bufr_dbuoyprof.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/temp_bufr_mbuoybprof.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/salt_bufr_mbuoybprof.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/bufr_tesacprof.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/bufr_trkobprof.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/bufr_sfcships.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/bufr_sfcshipsu.yaml
)

# create testinput dir
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/testinput)

# symlink
foreach(FILENAME ${test_input})
  file(RELATIVE_PATH FILENAME_REL ${PROJECT_SOURCE_DIR}/test/testinput/ ${FILENAME})
  file(CREATE_LINK ${FILENAME} ${PROJECT_BINARY_DIR}/test/testinput/${FILENAME_REL} SYMBOLIC)
endforeach(FILENAME)

# install
install(FILES ${test_input}
        DESTINATION "test/testinput/")

# create testrun dir
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/testrun)

# create testout dir
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/testoutput)

# create testreference dir
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/testreference)

# list of test reference files to install
list(APPEND test_reference
  ${PROJECT_SOURCE_DIR}/test/testreference/amsua_n19_gdas.yaml
)

# symlink
foreach(FILENAME ${test_reference})
  file(RELATIVE_PATH FILENAME_REL ${PROJECT_SOURCE_DIR}/test/testreference/ ${FILENAME})
  file(CREATE_LINK ${FILENAME} ${PROJECT_BINARY_DIR}/test/testreference/${FILENAME_REL} SYMBOLIC)
endforeach(FILENAME)

# install
install(FILES ${test_reference}
        DESTINATION "test/testreference/")

##### unit tests

# test for python coding norms
add_test(NAME test_gdasapp_check_python_norms
         COMMAND pycodestyle -v --config ./.pycodestyle ./ush ./scripts ./test
         WORKING_DIRECTORY ${PROJECT_SOURCE_DIR})

# test for ush/check_yaml_keys.py
add_test(NAME test_gdasapp_check_yaml_keys
         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/ush/check_yaml_keys.py ${PROJECT_BINARY_DIR}/test/testinput/check_yaml_keys_ref.yaml ${PROJECT_BINARY_DIR}/test/testinput/check_yaml_keys_test.yaml
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

# test to ensure all YAML in repo is valid YAML
#add_test(NAME test_gdasapp_check_valid_yaml
#         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/test/check_valid_yaml.py ${PROJECT_SOURCE_DIR}
#         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
# commented out above test because it does not really do as advertised with all these templates which are not valid yaml

# high level tests that require the global-workflow
# TODO(AFE) see GDASApp issue #1213
#if (WORKFLOW_TESTS)
#
#  # test for creating an experiment directory within the global-workflow
#  add_test(NAME test_gdasapp_setup_cycled_exp
#           COMMAND ${PROJECT_SOURCE_DIR}/test/setup_workflow_exp.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
#           WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/testrun)
#endif()

if (${BUILD_GDASBUNDLE})
  add_subdirectory(snow)      # snow da tests
  add_subdirectory(gw-ci)   # subset of the global-workflow ci tests
endif()

# gdas atm tests
add_subdirectory(atm)

# gdas aerosol tests
add_subdirectory(aero)

add_subdirectory(marine)
