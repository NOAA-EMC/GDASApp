##### get test data from EMC FTP server
# set URL and hash
set(URL "https://ftp.emc.ncep.noaa.gov/static_files/public/GDASApp")
set(SHA "75c4ce84028956c1ce050e07f70abc25c540492c3e1a40f6fa56d35182322e8e")
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

# list of test files to install
list(APPEND test_data
  ${CMAKE_CURRENT_BINARY_DIR}/testdata/atminc_compress.nc4
)

# install
install(FILES ${test_data}
        DESTINATION "test/testdata/")

# create testout dir
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/testoutput)

##### unit tests
# test for python coding norms
add_test(NAME test_gdasapp_check_python_norms
         COMMAND pycodestyle -v --config ./.pycodestyle ./ush ./scripts ./test
         WORKING_DIRECTORY ${PROJECT_SOURCE_DIR})
# test for ush/check_yaml_keys.py
add_test(NAME test_gdasapp_check_yaml_keys
         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/ush/check_yaml_keys.py ${PROJECT_SOURCE_DIR}/test/testinput/check_yaml_keys_ref.yaml ${PROJECT_SOURCE_DIR}/test/testinput/check_yaml_keys_test.yaml
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
# test to ensure all YAML in repo is valid YAML
add_test(NAME test_gdasapp_check_valid_yaml
         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/test/check_valid_yaml.py ${PROJECT_SOURCE_DIR} 
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
# test for ush/jediinc2fv3.py
add_test(NAME test_gdasapp_jedi_increment_to_fv3
         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/ush/jediinc2fv3.py ${PROJECT_BINARY_DIR}/test/testdata/atminc_compress.nc4 ${PROJECT_BINARY_DIR}/test/testoutput/fv_increment.nc 
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
