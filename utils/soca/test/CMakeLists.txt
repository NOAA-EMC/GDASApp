# Define a function to add tests with resource generation
function(add_test_with_resources test_name test_executable test_config resource_script mpi_command)
    set(test_working_dir ${PROJECT_BINARY_DIR}/test/gdasapp/${test_name})
    file(MAKE_DIRECTORY ${test_working_dir})

    set(test_driver ${test_working_dir}/run_test_${test_name}.py)

    # Generate the driver script
    file(WRITE ${test_driver}
"#!/usr/bin/env python3
import subprocess
import os
import shutil
import sys, shlex

work_dir = r'''${test_working_dir}'''
os.makedirs(work_dir, exist_ok=True)

args = sys.argv[1:]  # Capture the MPI command passed from CMake
mpi_command = shlex.split(args[0]) if len(args) == 1 else args

try:
    print('Setting up resources...')
    subprocess.run(['${Python3_EXECUTABLE}', '${resource_script}', '${PROJECT_SOURCE_DIR}'],
                   cwd=work_dir, check=True)

    print(f'Running test executable... {mpi_command}')
    subprocess.run(mpi_command + ['${CMAKE_BINARY_DIR}/bin/${test_executable}', '${test_config}'],
                   cwd=work_dir, check=True)

    print('Cleaning up...')
    for file in os.listdir(work_dir):
        if not file.endswith('.py'):
            file_path = os.path.join(work_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

except subprocess.CalledProcessError as e:
    print('Error during test execution:', e)
    sys.exit(1)
")

    # Make the script executable
    file(COPY ${test_driver} DESTINATION ${test_working_dir} FILE_PERMISSIONS OWNER_EXECUTE OWNER_WRITE OWNER_READ)

    add_test(NAME ${test_name}
             COMMAND ${Python3_EXECUTABLE} ${test_driver} ${mpi_command})
endfunction()

# Detect the hostname
# Note: Set IS_WORKSTATION=TRUE if you want to run the tests on a workstation type environement
execute_process(COMMAND hostname OUTPUT_VARIABLE HOSTNAME OUTPUT_STRIP_TRAILING_WHITESPACE)
if(HOSTNAME MATCHES "^hfe" OR
   HOSTNAME MATCHES "^ufe")
    set(IS_KNOWN_HPC TRUE)
    message(STATUS "Detected HPC environment: ${HOSTNAME}")
    set(MPI_COMMAND "${MPIEXEC_EXECUTABLE} ${MPIEXEC_NUMPROC_FLAG} 2 --time=00:02:00 --account=da-cpu --qos=batch")
else()
    set(IS_KNOWN_HPC FALSE)
    option(IS_WORKSTATION "Set to TRUE to enable workstation environment" OFF)
    if(IS_WORKSTATION)
        message(STATUS "Detected workstation environment: ${HOSTNAME}")
        set(MPI_COMMAND "${MPIEXEC_EXECUTABLE} ${MPIEXEC_NUMPROC_FLAG} 2")
    else()
        message(STATUS "Skipping GDAS app tests as IS_WORKSTATION is OFF")
        return()
    endif()
endif()

# gdas_incr_handler.x: Apply QC and convert the soca increment to a MOM6 IAU increment
add_test_with_resources(test_gdasapp_utils_incrhandler
                        gdas_incr_handler.x
                        ${PROJECT_SOURCE_DIR}/soca/test/testinput/gdas_incr_handler.yaml
                        ${PROJECT_SOURCE_DIR}/soca/test/generate_soca_resources.py
                        ${MPI_COMMAND})

# gdas_socahybridweights.x: Generate hybrid weights for B
add_test_with_resources(test_gdasapp_utils_hybridweights
                        gdas_socahybridweights.x
                        ${PROJECT_SOURCE_DIR}/soca/test/testinput/gdas_socahybridweights.yaml
                        ${PROJECT_SOURCE_DIR}/soca/test/generate_soca_resources.py
                        ${MPI_COMMAND})

# gdas_soca_setcorscales.x: Generate COR scales for C
add_test_with_resources(test_gdasapp_utils_setcorscales
                        gdas_soca_setcorscales.x
                        ${PROJECT_SOURCE_DIR}/soca/test/testinput/gdas_soca_setcorscales.yaml
                        ${PROJECT_SOURCE_DIR}/soca/test/generate_soca_resources.py
                        ${MPI_COMMAND})

# gdas_soca_diagb.x: Variance partitioning for the diagonal of B
add_test_with_resources(test_gdasapp_utils_diagb
                        gdas_soca_diagb.x
                        ${PROJECT_SOURCE_DIR}/soca/test/testinput/gdas_soca_diagb.yaml
                        ${PROJECT_SOURCE_DIR}/soca/test/generate_soca_resources.py
                        ${MPI_COMMAND})

# gdas_ens_handler.x: Ensemble members post processing
add_test_with_resources(test_gdasapp_utils_enshandler
                        gdas_ens_handler.x
                        ${PROJECT_SOURCE_DIR}/soca/test/testinput/gdas_ens_handler.yaml
                        ${PROJECT_SOURCE_DIR}/soca/test/generate_soca_resources.py
                        ${MPI_COMMAND})
