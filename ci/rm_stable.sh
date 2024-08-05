#!/bin/bash

stablefile=$1
olddir=$2

stabledate=`cat $stablefile`

base=`basename $2`

if [[ $base -ne $stabledate ]]; then
  rm -rf $2
fi
