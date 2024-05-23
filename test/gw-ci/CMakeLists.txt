# Setup the environement
set(HOMEgfs ${CMAKE_SOURCE_DIR}/../../..)
set(RUNTESTS ${CMAKE_CURRENT_BINARY_DIR}/../../test/gw-ci)

# List of g-w ci test to create
set(cycling_tests "C48mx500_3DVarAOWCDA" "C96_atmaerosnowDA" "C96C48_ufs_hybatmDA")

# Prepare the cycling ctests
foreach(pslot ${cycling_tests})
  set(YAML ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
  add_test(NAME ${pslot}
           COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/create_exp.sh ${YAML} ${pslot} ${HOMEgfs} ${RUNTESTS}"
           WORKING_DIRECTORY ${RUNTESTS})
  set_tests_properties(${pslot} PROPERTIES LABELS "manual")
endforeach()
