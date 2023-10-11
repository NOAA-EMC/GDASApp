#!/bin/bash
# run_hfo_hofx_test.sh
# This script is intended to simplify/automate large portions
# of the UFO acceptance for GDAS.
# This script will:
# - Create a working directory
# - Stage fix files, obs, geovals, etc.
# - Run the UFO test executable(s) necessary
# - Produce an EVA YAML
# - Run EVA
#-------------------------------------------------------------

# ==============================================================================
usage() {
  set +x
  echo
  echo "Usage: $0 [-c cycle] [-q] [-x] [-s] [-k] [-h] instrument"
  echo
  echo "  -c  cycle to run DEFAULT=2021080100"
  echo "  -q  run without data filtering"
  echo "  -x  don't run eva DEFAULT=run eva"
  echo "  -s  just produce eva stats plots DEFAULT=produce lots of plots"
  echo "  -k  keep output directory"
  echo "  -h  display this message and quit"
  echo
  exit 1
}

# ==============================================================================

cycle=2021080100
run_filtering=YES
run_eva=YES
eva_stats_only=NO
keep_output=NO 

while getopts "c:hsxq" opt; do
  case $opt in
    c)
      cycle=$OPTARG
      ;;
    q)
      run_filtering=NO
      ;;
    x)
      run_eva=NO 
      ;;
    s)
      eva_stats_only=YES
      ;;
    k)
      keep_output=YES
      ;;
    h|\?|:)
      usage
      ;;
  esac
done
shift $((OPTIND - 1))

if [ $# -ne 1 ]; then
   echo "Incorrect number of arguments"
   usage 
fi

obtype=$1

#--------------- User modified options below -----------------

machine=${machine:-orion} 

if [ $machine = orion ]; then
   if [ $run_filtering == NO ]; then
      workdir=/work2/noaa/da/$LOGNAME/ufoeval/$cycle/${obtype}_noqc
      echo "Run without data filtering"
   else
      workdir=/work2/noaa/da/$LOGNAME/ufoeval/$cycle/${obtype}
   fi
   GDASApp=${GDASApp:-/work2/noaa/da/$LOGNAME/git/GDASApp/} # Change this to your own branch
elif [ $machine = hera ]; then
   if [ $run_filtering == NO ]; then
      workdir=/scratch1/NCEPDEV/stmp2/$LOGNAME/ufoeval/$cycle/${obtype}_noqc
   else
      workdir=/scratch1/NCEPDEV/stmp2/$LOGNAME/ufoeval/$cycle/${obtype}
   fi
   GDASApp=${GDASApp:-/scratch1/NCEPDEV/da/$LOGNAME/git/GDASApp/} # Change this to your own branch
else
   echo "Machine " $machine "not found"
   exit 1
fi

if [ $keep_output = YES ]; then
  datetime=`date +%F:%T`
  workdir=${workdir}_datetime
fi

if [ $run_filtering == NO ]; then
   yamlpath=$GDASApp/parm/atm/obs/testing/swell/${obtype}_noqc.yaml
else
   yamlpath=$GDASApp/parm/atm/obs/testing/swell/${obtype}.yaml
fi

exename=test_ObsFilters.x

#-------------- Do not modify below this line ----------------
# paths that should only be changed by an expert user

dataprocdate=20230811 # Production date of test data

obtype_short=${obtype:0:4}
if [ $obtype_short = "cris" ] || [ $obtype_short = "iasi" ] || [ $obtype_short = "hirs" ] || [ $obtype_short = "sevi" ] || \
   [ $obtype_short = "avhr" ] || [ $obtype_short = "mhs_" ] || [ $obtype_short = "ssmi" ] || [ $obtype_short = "amsu" ] || \
   [ $obtype_short = "atms" ]; then
   aircraft="NO"
   radiance="YES"
elif [ $obtype_short = "airc" ]; then
   aircraft="YES"
   radiance="NO"
else
   aircraft="NO"
   radiance="NO"
fi

if [ $machine = orion ]; then
    #export Datapath='/work2/noaa/da/eliu/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/'$dataprocdate 
    export Datapath='/work2/noaa/da/acollard/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/'$dataprocdate #ADC
    FixDir=/work2/noaa/da/cmartin/GDASApp/fix
elif [ $machine = hera ]; then
    export Datapath='/scratch1/NCEPDEV/da/Emily.Liu/UFO_eval/data/gsi_geovals_l127/nofgat_aug2021/'$dataprocdate
    FixDir=/scratch1/NCEPDEV/da/Cory.R.Martin/GDASApp/fix
else
   echo "Machine " $machine "not found"
   exit
fi

GeoDir=$Datapath/geovals/
ObsDir=$Datapath/obs/
BCDir=$Datapath/bc/

# other variables that should not change often
export CDATE=$cycle
export assim_freq=6
export GDATE=$(date +%Y%m%d%H -d "${CDATE:0:8} ${CDATE:8:2} - ${assim_freq} hours")
export PDY=${CDATE:0:8}
export cyc=${CDATE:8:2}
export gPDY=${GDATE:0:8}
export gcyc=${GDATE:8:2}
export CASE="C768"
export CASE_ANL="C384"
export LEVS="128"

# Load Modules for GDASApp
module use $GDASApp/modulefiles
module load GDAS/$machine
export PYTHONPATH=$GDASApp/ush:$PYTHONPATH

# Create and set up the working directory
[ -d $workdir ] && rm -rf $workdir
mkdir -p $workdir

# Link CRTM coefficients
[ -d $workdir/crtm ] && rm -rf $workdir/crtm
ln -sf $FixDir/crtm/2.4.0 $workdir/crtm

# copy BC files
if [ $radiance = "YES" ] || [ $aircraft = "YES" ]; then
  cp -rf $BCDir/${obtype}*${GDATE}* $workdir/.
fi

# Copy obs and geovals
cp -rf $GeoDir/${obtype}_geoval_${cycle}*.nc4 $workdir/.
cp -rf $ObsDir/${obtype}_obs_${cycle}*.nc4 $workdir/.

# Link executable
ln -sf $GDASApp/build/bin/$exename $workdir/.

echo "Generating YAML"

# Copy/generate YAML for test executable
# First, create the input YAMLs for the genYAML script
export DATA=./
export COMPONENT=atmos
export OPREFIX=gdas.t${cyc}z
export APREFIX=gdas.t${cyc}z
export GPREFIX=gdas.t${gcyc}z

cat > $workdir/temp.yaml << EOF
window begin: '{{ WINDOW_BEGIN | to_isotime }}'
window end: '{{ WINDOW_END | to_isotime }}'
observations:
- !INC $yamlpath
EOF
$GDASApp/ush/genYAML --input $workdir/temp.yaml --output $workdir/${obtype}_${cycle}.yaml

if [ $? -ne 0 ]; then
   echo "YAML creation failed"
   exit 1
fi

echo "Running executable"

# Run executable
cd $workdir
./$exename ${obtype}_${cycle}.yaml

if [ $? -ne 0 ]; then
   echo "*************** Running UFO failed ****************"
   RC=1
   if [ $run_eva == YES ]; then
       echo "Running EVA for diagnostic purposes"
   else
       exit 1
   fi
else
   RC=0
   if [ $run_eva == YES ]; then
       echo "Running EVA"
   else
       exit 0
   fi
fi

# Load EVA modules
module load EVA/$machine

# Generate EVA YAML
if [ $radiance = "YES" ]; then
  if [ $eva_stats_only = "YES" ]; then
    $GDASApp/ush/eva/gen_eva_obs_yaml.py -i ./${obtype}_${cycle}.yaml -t $GDASApp/ush/eva/jedi_gsi_compare_rad_summary.yaml -o $workdir
  else 
    $GDASApp/ush/eva/gen_eva_obs_yaml.py -i ./${obtype}_${cycle}.yaml -t $GDASApp/ush/eva/jedi_gsi_compare_rad.yaml -o $workdir
  fi
else
  $GDASApp/ush/eva/gen_eva_obs_yaml.py -i ./${obtype}_${cycle}.yaml -t $GDASApp/ush/eva/jedi_gsi_compare_conv.yaml -o $workdir
fi

# Run EVA
for yaml in $(ls eva_*.yaml); do
  eva $yaml
done

if [ $? -ne 0 ]; then
   echo "EVA failed"
   exit 1
else
   exit $RC
fi
