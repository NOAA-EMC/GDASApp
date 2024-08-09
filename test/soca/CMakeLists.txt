# Copy the bkg files
# ------------------
set(TESTDATA ${PROJECT_BINARY_DIR}/test/testdata )


# Symlink test input yaml files
# -----------------------------
# create testinput dir
set (TESTINPUT_DIR ${PROJECT_BINARY_DIR}/test/soca/testinput)

file(MAKE_DIRECTORY ${TESTINPUT_DIR})

# symlink
foreach(FILENAME ${test_input})
	get_filename_component(filename ${FILENAME} NAME)
	execute_process( COMMAND ${CMAKE_COMMAND} -E create_symlink
		${FILENAME}
		${TESTINPUT_DIR}
	)
endforeach(FILENAME)

# install
install(FILES ${test_input}
        DESTINATION "test/testinput/")

# Test exgdas scripts from the global-worflow
if (WORKFLOW_TESTS)
  add_subdirectory(gw)
endif()

# test for ush/socaincr2mom6.py
add_test(NAME test_gdasapp_soca_nsst_increment_to_mom6
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/socaincr2mom6.sh ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca)
set_tests_properties(
        test_gdasapp_soca_nsst_increment_to_mom6
PROPERTIES
ENVIRONMENT "data=${TESTDATA};PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH}")





set(MARINE_BUFR2IODA_DIR ${PROJECT_SOURCE_DIR}/ush/ioda/bufr2ioda/marine)
set(MARINE_BUFR2IODA_DIR ${MARINE_BUFR2IODA_DIR}/b2i)
set(CONFIG_DIR ${PROJECT_SOURCE_DIR}/test/soca/testinput)
set(TESTREF_DIR ${PROJECT_SOURCE_DIR}/test/soca/testref)

function(ADD_INSITU_TEST testname)
	set(TEST bufr2ioda_insitu_${testname})
	set(CONFIG_FILE ${TEST}_2021063006.json)
	set(TESTREF_FILE ${TEST}_2021063006.ref)

	add_test(
		NAME test_${TEST}
		COMMAND ${MARINE_BUFR2IODA_DIR}/${TEST}.py -c ${CONFIG_DIR}/${CONFIG_FILE} -t ${TESTREF_DIR}/${TESTREF_FILE}
		WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca
	)
endfunction()


ADD_INSITU_TEST(profile_argo)
ADD_INSITU_TEST(profile_bathy)
ADD_INSITU_TEST(profile_glider)
# ADD_INSITU_TEST(profile_marinemammal)
ADD_INSITU_TEST(profile_tesac)
ADD_INSITU_TEST(profile_xbtctd)
# ADD_INSITU_TEST(surface_altkob)
ADD_INSITU_TEST(surface_trkob)
