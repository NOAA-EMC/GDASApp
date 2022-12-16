#!/bin/bash
bindir=$1
srcdir=$2

cat > testoutput/genYAML_example.yaml << EOF
template: ${srcdir}/parm/atm/variational/3dvar_dripcg.yaml
output: ${bindir}/test/testoutput/genYAML_output_3dvar.yaml
config:
  BERROR_YAML: \${PARMgfs}/atm/berror/staticb_bump.yaml
  OBS_YAML_DIR: \${PARMgfs}/atm/obs/config
  COMPONENT: atmos
  layout_x: '1'
  layout_y: '2'
  OBS_LIST: ${srcdir}/parm/atm/obs/lists/gdas_prototype.yaml
  OPREFIX: gdas.t00z.
  CDATE: '2022033000'
  valid_time: '2022-03-30T00:00:00Z'
  atm_window_length: PT6H
EOF
