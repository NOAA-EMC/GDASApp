# test for creating an experiment directory within the global-workflow
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/testrun)
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/concatioda)


# Identify machine
set(MACHINE "container")
IF (IS_DIRECTORY /work2/noaa/da)
  set(MACHINE "orion")
  set(PARTITION "debug")
ENDIF()
IF (IS_DIRECTORY /scratch2/NCEPDEV/)
  set(MACHINE "hera")
  set(PARTITION "hera")
ENDIF()

# Test ioda-concatenation
add_test(NAME test_gdasapp_soca_concatioda
         COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/test/soca/gw/test_concatioda.py ${PROJECT_BINARY_DIR}/test/soca/obs
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/concatioda)
       set_tests_properties(test_gdasapp_soca_concatioda
      PROPERTIES
      ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH}")

# Clean-up
add_test(NAME test_gdasapp_soca_run_clean
  COMMAND  ${CMAKE_COMMAND} -E remove_directory ${PROJECT_BINARY_DIR}/test/soca/gw/testrun/testjjobs)


# Test JGDAS_GLOBAL_OCEAN_ANALYSIS_*
set(jjob_list "JGDAS_GLOBAL_OCEAN_ANALYSIS_PREP"
              "JGDAS_GLOBAL_OCEAN_ANALYSIS_BMAT"
              "JGDAS_GLOBAL_OCEAN_ANALYSIS_BMAT_VRFY"
              "JGDAS_GLOBAL_OCEAN_ANALYSIS_RUN"
              "JGDAS_GLOBAL_OCEAN_ANALYSIS_CHKPT"
              "JGDAS_GLOBAL_OCEAN_ANALYSIS_POST"
              "JGDAS_GLOBAL_OCEAN_ANALYSIS_VRFY")

set(setup "")
foreach(jjob ${jjob_list})

  # substitute a few variables in the test yaml
  message("ctest for ${jjob}")
  set(HOMEgfs ${PROJECT_SOURCE_DIR}/../..)
  set(JJOB ${jjob})
  configure_file(${PROJECT_SOURCE_DIR}/test/soca/gw/run_jjobs.yaml.test
                 ${PROJECT_BINARY_DIR}/test/soca/gw/testrun/run_jjobs_${jjob}.yaml)
  set(test_name "test_gdasapp_soca_${jjob}")
  add_test(NAME ${test_name}
    COMMAND ${PROJECT_SOURCE_DIR}/ush/soca/run_jjobs.py
         -y ${PROJECT_BINARY_DIR}/test/soca/gw/testrun/run_jjobs_${jjob}.yaml
         ${setup}
    WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/testrun)

  set(setup "--skip") # Only run the setup of the first test, if not, it will hang
                      # waiting for standard input from setup_expt.py
endforeach()
