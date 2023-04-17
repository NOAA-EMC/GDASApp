#!/bin/bash
set -ex
bindir=$1
srcdir=$2

${srcdir}/ush/socaincr2mom6.py --help

#--incr "${soca_incr}" \
#                                             --bkg "${DATA}/INPUT/MOM.res.nc" \
#                                             --grid "${DATA}/soca_gridspec.nc" \
#                                             --out "${mom6_iau_incr}" \
#                                             --nsst_yaml
