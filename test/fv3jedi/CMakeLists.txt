# Subdirectories
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/fv3jedi/testinput)
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/fv3jedi/testoutput)
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/fv3jedi/fv3jedi)

# Test YAMLs
file(CREATE_LINK ${PROJECT_SOURCE_DIR}/test/fv3jedi/testinput/gdasapp_fv3jedi_jediinc2fv3.yaml ${PROJECT_BINARY_DIR}/test/fv3jedi/testinput/gdasapp_fv3jedi_jediinc2fv3.yaml SYMBOLIC)

# Test reference files
file(CREATE_LINK ${PROJECT_SOURCE_DIR}/test/fv3jedi/testoutput/gdasapp_fv3jedi_jediinc2fv3.ref ${PROJECT_BINARY_DIR}/test/fv3jedi/testoutput/gdasapp_fv3jedi_jediinc2fv3.ref SYMBOLIC)

# FV3 files
file(CREATE_LINK ${PROJECT_SOURCE_DIR}/parm/io/fv3jedi_fieldmetadata_fv3inc.yaml ${PROJECT_BINARY_DIR}/test/fv3jedi/fv3jedi/fv3jedi_fieldmetadata_fv3inc.yaml SYMBOLIC)
file(CREATE_LINK ${PROJECT_SOURCE_DIR}/parm/io/fv3jedi_fieldmetadata_history.yaml ${PROJECT_BINARY_DIR}/test/fv3jedi/fv3jedi/fv3jedi_fieldmetadata_history.yaml SYMBOLIC)
file(CREATE_LINK ${PROJECT_SOURCE_DIR}/sorc/fv3-jedi/test/Data/fv3files/akbk127.nc4 ${PROJECT_BINARY_DIR}/test/fv3jedi/fv3jedi/akbk127.nc4 SYMBOLIC)
file(CREATE_LINK ${PROJECT_SOURCE_DIR}/sorc/fv3-jedi/test/Data/fv3files/fmsmpp.nml ${PROJECT_BINARY_DIR}/test/fv3jedi/fv3jedi/fmsmpp.nml SYMBOLIC)
file(CREATE_LINK ${PROJECT_SOURCE_DIR}/sorc/fv3-jedi/test/Data/fv3files/field_table_gfdl ${PROJECT_BINARY_DIR}/test/fv3jedi/fv3jedi/field_table_gfdl SYMBOLIC)

# Tests
add_test(NAME test_gdasapp_fv3jedi_jediinc2fv3
         COMMAND srun -n6 ${CMAKE_BINARY_DIR}/bin/gdas_fv3jedi_jediinc2fv3.x ${PROJECT_BINARY_DIR}/test/fv3jedi/testinput/gdasapp_fv3jedi_jediinc2fv3.yaml
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/fv3jedi)

