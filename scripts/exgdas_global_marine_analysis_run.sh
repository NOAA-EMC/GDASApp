#!/bin/bash
################################################################################
####  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exgdas_global_marine_analysis_run.sh
# Script description:  Runs the global marine analysis with SOCA
#
# Author: Guillaume Vernieres        Org: NCEP/EMC     Date: 2022-04-24
#
# Abstract: This script makes a global model ocean sea-ice analysis using SOCA
#
# $Id$
#
# Attributes:
#   Language: POSIX shell
#   Machine: Orion
#
################################################################################

#  Set environment.
export VERBOSE=${VERBOSE:-"YES"}
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXECUTING $0 $* >&2
   set -x
fi

#  Directories
pwd=$(pwd)

#  Utilities
export NLN=${NLN:-"/bin/ln -sf"}

# function that converts a soca incr to something MOM6 is happy with
function socaincr2mom6 {
  incr=$1
  bkg=$2
  grid=$3
  incr_out=$4

  scratch=scratch_socaincr2mom6
  mkdir -p $scratch
  cd $scratch

  echo "at socaincr2mom6" $bkg $grid

  cp $incr inc.nc                   # TODO: use accumulated incremnet, not outerloop intermediates
  ncks -A -C -v h $bkg inc.nc       # Replace h incrememnt (all 0's) by h background (expected by MOM)
  ncrename -d zaxis_1,Layer inc.nc  # Rename zaxis_1 to Layer
  ncks -A -C -v Layer $bkg inc.nc   # Replace dimension-less Layer with dimensional Layer
  mv inc.nc inc_tmp.nc              # ... dummy copy
  ncwa -O -a Time inc_tmp.nc inc.nc # Remove degenerate Time dimension
  ncks -A -C -v lon $grid inc.nc    # Add longitude
  ncks -A -C -v lat $grid inc.nc    # Add latitude
  mv inc.nc $incr_out
}

function bump_vars()
{
    tmp=$(ls -d ${1}_* )
    lov=()
    for v in $tmp; do
        lov[${#lov[@]}]=${v#*_}
    done
    echo "$lov"
}

function concatenate_bump()
{
    bumpdim=$1
    # Concatenate the bump files
    vars=$(bump_vars $bumpdim)
    n=$(wc -w <<< "$vars")
    echo "concatenating $n variables: $vars"
    lof=$(ls ${bumpdim}_${vars[0]})
    echo $lof
    for f in $lof; do
        bumpbase=${f#*_}
        output=bump/${bumpdim}_$bumpbase
        lob=$(ls ${bumpdim}_*/*$bumpbase)
        for b in $lob; do
            ncks -A $b $output
        done
    done
}

function clean_yaml()
{
    mv $1 tmp_yaml;
    sed -e "s/'//g" tmp_yaml > $1
}

# This is a hack for Orion. Remove when nco is built as part of the stack
# loading nco should only be done at runtime currently since it reloads
# udunits/2.2.28 => udunits/2.2.26
if [[ "$HOSTNAME" =~ .*"Orion".* ]]; then
    module load nco/4.9.3
fi

################################################################################
# generate soca geometry
# TODO (Guillaume): Should not use all pe's for the grid generation
# TODO (Guillaume): Does not need to be generated at every cycles, store in static dir?
$APRUN_SOCAANAL $JEDI_BIN/soca_gridgen.x gridgen.yaml 2>gridgen.err

################################################################################
# Generate the parametric diag of B
$APRUN_SOCAANAL $JEDI_BIN/soca_convertincrement.x parametric_stddev_b.yaml 2>parametric_stddev_b.err

################################################################################
# Set decorrelation scales for bump C
$APRUN_SOCAANAL $JEDI_BIN/soca_setcorscales.x soca_setcorscales.yaml 2>soca_setcorscales.err

# 2D C from bump
yaml_list=`ls soca_bump2d_C*.yaml`
for yaml in $yaml_list; do
    # TODO (G, C, R, ...): problem with ' character when reading yaml, removing from file for now
    clean_yaml $yaml
    $APRUN_SOCAANAL $JEDI_BIN/soca_error_covariance_training.x $yaml 2>$yaml.err
done
concatenate_bump 'bump2d'

# 3D C from bump
yaml_list=`ls soca_bump3d_C*.yaml`
for yaml in $yaml_list; do
    clean_yaml $yaml
    $APRUN_SOCAANAL $JEDI_BIN/soca_error_covariance_training.x $yaml 2>$yaml.err
done
concatenate_bump 'bump3d'

################################################################################
# run 3DVAR FGAT
clean_yaml var.yaml
$APRUN_SOCAANAL $JEDI_BIN/soca_var.x var.yaml 2>var.err


# Prepare increment for MOM6 iau
if [[ "$DA_OCN_IAU" =~ [yYtT1] ]]; then
    # TODO: make sure it works when io layout is other than 1,1
   #( socaincr2mom6 `ls $INCR_TMP_DIR/ocn*.var.iter*` $BKGRST_DIR/MOM.res.nc `readlink soca_gridspec.nc` $INCR_TMP_DIR/inc.nc )
    # Make sure the last (most recent) increment file put into socaincr2mom6 as $1
    ( socaincr2mom6 `ls -t $INCR_TMP_DIR/ocn.*iter*.incr* | head -1` $BKGRST_DIR/MOM.res.nc $SOCAGRID_DIR/soca_gridspec.nc $INCR_TMP_DIR/inc.nc )
fi



################################################################################
set +x
if [ $VERBOSE = "YES" ]; then
   echo $(date) EXITING $0 with return code $err >&2
fi
exit $err

################################################################################
