# WCDA test similar to what is tested in the gw-ci
set(pslot wcda-gwci)
set(HOMEgfs ${CMAKE_SOURCE_DIR}/../../..)
set(RUNTESTS ${CMAKE_CURRENT_BINARY_DIR}/../../test/gw-ci)
set(YAML ${HOMEgfs}/ci/cases/pr/C48mx500_3DVarAOWCDA.yaml)

add_test(NAME wcda_ci
         COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/create_exp.sh ${YAML} ${pslot} ${HOMEgfs} ${RUNTESTS}"
         WORKING_DIRECTORY ${RUNTESTS})
