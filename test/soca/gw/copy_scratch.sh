#!/bin/bash
set -e

project_binary_dir=$1

cp -r ${project_binary_dir}/test/soca/gw/testrun/testjjobs/RUNDIRS/gdas_test/gdasocnanal_12/* ${project_binary_dir}/test/soca/gw/apps_scratch
