#!/bin/bash
bindir=$1
srcdir=$2

cat > testoutput/genYAML_example_land.yaml << EOF
template: ${srcdir}/parm/land/letkfoi/letkfoi.yaml
output: ${bindir}/test/testoutput/genYAML_output_letkfoi.yaml
config:
  BERROR_YAML: \${PARMgfs}/atm/berror/staticb_bump.yaml
  OBS_YAML_DIR: \${PARMgfs}/land/obs/config
  COMPONENT: land
  layout_x: '1'
  layout_y: '2'
  OBS_LIST: ${srcdir}/parm/land/obs/lists/gdas_land_prototype.yaml
  OPREFIX: gdas.t18z.
  CDATE: '2021032318'
  PDY: '20210323'
  cyc: '18'
  valid_time: '2021-03-23T18:00:00Z'
  atm_window_length: PT6H
  land_window_length: PT6H
  CASE: 'C48'
  CASE_ENKF: 'C48'
  LEVS: '128'
EOF
