add_test(NAME test_check_yaml_keys
         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/ush/check_yaml_keys.py ${PROJECT_SOURCE_DIR}/test/testinput/check_yaml_keys_ref.yaml ${PROJECT_SOURCE_DIR}/test/testinput/check_yaml_keys_test.yaml
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)
