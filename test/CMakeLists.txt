add_test(NAME test_check_yaml_keys
         COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/ush/check_yaml_keys.py ${CMAKE_SOURCE_DIR}/test/testinput/check_yaml_keys_ref.yaml ${CMAKE_SOURCE_DIR}/test/testinput/check_yaml_keys_test.yaml
         WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/test/)
