#!/bin/bash
set -ex

srcdir=$1

mom6_iau_incr="gdas.t12z.ocn.incr.nc"

cat > nsst.yaml << EOF
sfc_fcst: ${data}/gdas.t06z.sfcf006.nc
sfc_ana: ${data}/gdas.t12z.sfcanl.nc
nlayers: 2
EOF

${srcdir}/ush/socaincr2mom6.py --incr "${data}/ocn.3dvarfgat_pseudo.incr.2018-04-15T09:00:00Z.nc" \
                               --bkg "${data}/gdas.t06z.ocnf006.nc" \
                               --grid "${data}/gdas.t09z.ocngrid.nc" \
                               --out "${mom6_iau_incr}" \
                               --nsst_yaml "nsst.yaml"
