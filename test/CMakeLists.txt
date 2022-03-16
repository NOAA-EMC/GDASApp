add_test(NAME test_check_yaml_keys
         COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/ush/check_yaml_keys.py
         WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/test/)