# Setup the environement
set(HOMEgfs ${CMAKE_SOURCE_DIR}/../../..)
set(RUNTESTS ${CMAKE_CURRENT_BINARY_DIR}/../../test/gw-ci)

# List of g-w ci test to create
set(cycling_tests "C48mx500_3DVarAOWCDA" "C96_atmaerosnowDA" "C96C48_ufs_hybatmDA")

# Prepare the cycling ctests
# --------------------------
foreach(pslot ${cycling_tests})
  set(YAML ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
  add_test(NAME ${pslot}
           COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/create_exp.sh ${YAML} ${pslot} ${HOMEgfs} ${RUNTESTS}"
           WORKING_DIRECTORY ${RUNTESTS})
  set_tests_properties(${pslot} PROPERTIES LABELS "manual")
endforeach()

# Run tasks for C48mx500_3DVarAOWCDA
# ----------------------------------
set(pslot C48mx500_3DVarAOWCDA)

# gdasfcst from the 1/2 cycle
set(CYCLE 202103241200)
set(TASK_NAME gdasfcst)
add_test(NAME ${pslot}_gdasfcst_202103241200
         COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh ${pslot} ${TASK_NAME} ${CYCLE}"
         WORKING_DIRECTORY ${RUNTESTS})
set_tests_properties(${pslot} PROPERTIES LABELS "manual")

# Run the marine DA tasks
set(tasks "gdasprepoceanobs" "gdasocnanalprep" "gdasocnanalbmat" "gdasocnanalrun" "gdasocnanalchkpt" "gdasocnanalpost")
set(CYCLE 202103241800)
foreach(task ${tasks})
  set(TASK_NAME ${task})
  add_test(NAME ${pslot}_${TASK_NAME}_${CYCLE}
           COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh ${pslot} ${TASK_NAME} ${CYCLE}"
           WORKING_DIRECTORY ${RUNTESTS})
  set_tests_properties(${pslot} PROPERTIES LABELS "manual")
endforeach()
