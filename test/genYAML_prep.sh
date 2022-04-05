#!/bin/bash
bindir=$1
srcdir=$2

cat > testoutput/genYAML_example.yaml << EOF
template: ${srcdir}/parm/atm/variational/3dvar_dripcg.yaml
output: ${bindir}/test/testoutput/genYAML_output_3dvar.yaml
config:
  paths: $<< ${srcdir}/parm/atm/common/paths.yaml
  atm: true
  layout_x: '1'
  layout_y: '2'
  BKG_DIR: /this/is/not/a/real/path
  OBS_LIST: ${srcdir}/parm/atm/obs/lists/gdas_prototype.yaml
  fv3jedi_fix_dir: Data/fv3files
  fv3jedi_fieldset_dir: Data/fieldsets
  ANL_DIR: /fake/path/to/analysis
  fv3jedi_staticb_dir: /fake/path/to/berror
  BIAS_DIR: /fake/path/to/biascoeff
  CRTM_COEFF_DIR: /fake/path/to/crtm
  BIAS_PREFIX: gdas.t18z
  BIAS_DATE: '2022033000'
  DIAG_DIR: /fake/output/path
  OBS_DIR: /fake/path/to/obs
  OBS_PREFIX: gdas.t00z
  OBS_DATE: '2022033000'
  valid_time: '2022-03-30T00:00:00Z'
  atm_window_length: PT6H
EOF
