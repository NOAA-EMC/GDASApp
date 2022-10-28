##### get test data from EMC FTP server
# set URL and hash
set(URL "https://ftp.emc.ncep.noaa.gov/static_files/public/GDASApp")
set(SHA "43c9e0990ea663e6da1c21121391c10731f53f31838dae112e0e63e5c38f6af7")
string(SUBSTRING ${SHA} 0 6 SHORTSHA)
set(TAR "gdasapp-fix-${SHORTSHA}.tgz")
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
# Extract downloaded tarball.
file(ARCHIVE_EXTRACT INPUT ${CMAKE_CURRENT_BINARY_DIR}/${TAR}
  DESTINATION ${CMAKE_CURRENT_BINARY_DIR})

# list of test binary/data files to install
list(APPEND test_data
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/atminc_compress.nc4
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/adt.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/sst.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/sss.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/prof.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/icec.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/icefb.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/MOM.res.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_09.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_10.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_11.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_12.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_13.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_14.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/ocn_da_2018_04_15_15.nc
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/iced.2019-04-15-43200.nc
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
  ${PROJECT_SOURCE_DIR}/test/testinput/amsua_n19_ewok.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/bufr_dbuoy.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/bufr_mbuoyb.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/bufr_tesac.yaml
  ${PROJECT_SOURCE_DIR}/test/testinput/bufr_trkob.yaml
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
add_test(NAME test_gdasapp_check_valid_yaml
         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/test/check_valid_yaml.py ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
# test for ush/jediinc2fv3.py
add_test(NAME test_gdasapp_jedi_increment_to_fv3
         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/ush/jediinc2fv3.py ${PROJECT_BINARY_DIR}/test/testdata/atmges_compress.nc4 ${PROJECT_BINARY_DIR}/test/testdata/atminc_compress.nc4 ${PROJECT_BINARY_DIR}/test/testoutput/fv_increment.nc
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
# test for YAML generation from a template
add_test(NAME test_gdasapp_generate_yaml_func
         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/test/test_generate_yaml.py --parm ${PROJECT_SOURCE_DIR}/parm/
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
set_tests_properties(
         test_gdasapp_generate_yaml_func
PROPERTIES
         ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH};PARMgfs=${PROJECT_SOURCE_DIR}/parm;gPDY=20220330;gcyc=00;PDY=20220330;cyc=06;assim_freq=6"
)
add_test(NAME test_gdasapp_genYAML_prep
         COMMAND ${PROJECT_SOURCE_DIR}/test/genYAML_prep.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
add_test(NAME test_gdasapp_genYAML_run
         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/ush/genYAML --config ${PROJECT_BINARY_DIR}/test/testoutput/genYAML_example.yaml
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
set_tests_properties(
         test_gdasapp_genYAML_run
PROPERTIES
         ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH};PARMgfs=${PROJECT_SOURCE_DIR}/parm"
)
# test for converting ewok yaml to gdas
add_test(NAME test_gdasapp_convert_ewok_yaml
         COMMAND ${PROJECT_SOURCE_DIR}/test/convert_ewok_yaml.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

# soca tests
add_subdirectory(soca)

# gdas atm tests
add_subdirectory(atm)
