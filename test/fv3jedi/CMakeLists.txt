file(CREATE_LINK ${PROJECT_SOURCE_DIR}/parm/io/fv3jedi_fieldmetadata_fv3inc.yaml ${PROJECT_BINARY_DIR}/test/fv3jedi/fv3jedi_fieldmetadata_fv3inc.yaml SYMBOLIC)

file(CREATE_LINK ${PROJECT_SOURCE_DIR}/parm/io/fv3jedi_fieldmetadata_history.yaml ${PROJECT_BINARY_DIR}/test/fv3jedi/fv3jedi_fieldmetadata_history.yaml SYMBOLIC)

file(CREATE_LINK ${PROJECT_SOURCE_DIR}/test/fv3jedi/testinput/gdas_jediinc2fv3.yaml ${PROJECT_BINARY_DIR}/test/fv3jedi/testinput/gdas_jediinc2fv3.yaml SYMBOLIC)

file(CREATE_LINK ${PROJECT_SOURCE_DIR}/test/fv3jedi/testoutput/gdasapp_jedi_increment_to_fv3.ref ${PROJECT_BINARY_DIR}/test/fv3jedi/testoutput/gdasapp_jedi_increment_to_fv3.ref SYMBOLIC)

#list(APPEND test_input
#  ${PROJECT_SOURCE_DIR}/test/fv3jedi/testinput/gdas_jediinc2fv3.yaml
#)

add_test(NAME test_gdasapp_jedi_increment_to_fv3_new
         COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_jediinc2fv3.x ${PROJECT_BINARY_DIR}/test/fv3jedi/testinput/gdas_jediinc2fv3.yaml
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/)

