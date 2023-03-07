#!/bin/bash
bindir=$1
srcdir=$2

cat > testoutput/genYAML_example_aero.yaml << EOF
template: ${srcdir}/parm/aero/variational/3dvar_gfs_aero.yaml
output: ${bindir}/test/testoutput/genYAML_output_3dvar_gfs_aero.yaml
config:
  BERROR_YAML: \${PARMgfs}/aero/berror/staticb_bump.yaml
  OBS_YAML_DIR: \${PARMgfs}/aero/obs/config
  COMPONENT: chem 
  layout_x: '8'
  layout_y: '8'
  OBS_LIST: ${srcdir}/parm/aero/obs/lists/gdas_aero_prototype.yaml
  OPREFIX: gdas.t06z.
  CDATE: '2019061400'
  PDY: '20190614'
  cyc: '06'
  valid_time: '2019-06-14T06:00:00Z'
  aero_window_length: PT6H
  CASE: 'C96'
  CASE_ENKF: 'C48'
  LEVS: '128'
EOF
