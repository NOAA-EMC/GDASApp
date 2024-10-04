#!/usr/bin/env python3
import os
import datetime as dt
import logging
import subprocess
import csv
import shutil
import glob
import argparse
import yaml

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                    level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

predictors = [
    'constant',
    'zenith_angle',
    'cloud_liquid_water',
    'lapseRate_order_2',
    'lapseRate',
    'cosine_of_latitude_times_orbit_node',
    'sine_of_latitude',
    'emissivityJacobian',
    'sensorScanAngle_order_4',
    'sensorScanAngle_order_3',
    'sensorScanAngle_order_2',
    'sensorScanAngle',
]


def run_satbias_conv(config):
    # run ioda-converters satbias converter to take GSI satbias file
    # and create UFO compatible input files
    # get times from config
    startTime = config['start time']
    endTime = config['end time']
    assim_freq = int(config['assim_freq'])
    # get paths from config
    gsi_bc_root = config['gsi_bc_root']
    ufo_bc_root = config['ufo_bc_root']
    work_root = config['work_root']
    converter_exe = config['satbias2ioda']
    cdump = config.get('dump', 'gdas')
    # loop through all cycles
    nowTime = startTime
    while nowTime <= endTime:
        cdate = nowTime.strftime("%Y%m%d%H")
        pdy = nowTime.strftime("%Y%m%d")
        cyc = nowTime.strftime("%H")
        logging.info(f'Processing sat bias files for cycle: {cdate}')
        # create working directory
        workdir = os.path.join(work_root, f'{cdump}.{pdy}', cyc, 'atmos')
        os.makedirs(workdir, exist_ok=True)
        # link the GSI files to the working directory
        cycle_in_dir = os.path.join(gsi_bc_root, f'{cdump}.{pdy}', cyc, 'atmos')
        prefix = f"{cdump}.t{cyc}z"
        abias_path = os.path.join(cycle_in_dir, prefix + '.abias')
        abias_pc_path = os.path.join(cycle_in_dir, prefix + '.abias_pc')
        orig_paths = [converter_exe, abias_path, abias_pc_path]
        new_paths = [
            os.path.join(workdir, 'satbias2ioda.x'),
            os.path.join(workdir, 'satbias_crtm_in'),
            os.path.join(workdir, 'satbias_crtm_pc'),
        ]
        for src, dest in zip(orig_paths, new_paths):
            if os.path.exists(dest):
                os.unlink(dest)
            os.symlink(src, dest)
        # open the text file to get a list of satellites/sensors to process
        satlist = []
        with open(new_paths[1]) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                splitrow = row[0].split()
                if splitrow[1] not in satlist:
                    try:
                        a = float(splitrow[1])
                    except ValueError:
                        if len(splitrow[1]) > 0:
                            satlist.append(splitrow[1])
        # loop through satellites/sensors to write tlapmean txt file
        for sat in satlist:
            outstr = ''
            outfile = os.path.join(workdir, f'{sat}_tlapmean.txt')
            with open(new_paths[1]) as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    splitrow = row[0].split()
                    if splitrow[1] == sat:
                        outstr = outstr + f'{sat} {splitrow[2]} {splitrow[3]}\n'
            with open(outfile, 'w') as f:
                f.write(outstr)
        # create YAML for input to converter
        outyaml = os.path.join(workdir, 'satbias_converter.yaml')
        with open(outyaml, 'w') as f:
            f.write('input coeff file: satbias_crtm_in\n')
            f.write('input err file: satbias_crtm_pc\n')
            f.write('default predictors: &default_preds\n')
            for pred in predictors:
                f.write(f'- {pred}\n')
            f.write('output:\n')
            for sat in satlist:
                f.write(f'- sensor: {sat}\n')
                f.write(f'  output file: {sat}_satbias.nc\n')
                f.write('  predictors: *default_preds\n')
        # run executable
        runcmd = f'./satbias2ioda.x satbias_converter.yaml'
        p = subprocess.Popen(runcmd, shell=True, cwd=workdir)
        p.communicate()
        # copy output files to output directory
        outdir = os.path.join(ufo_bc_root, f'{cdump}.{pdy}', cyc, 'atmos')
        os.makedirs(outdir, exist_ok=True)
        ncfiles = glob.glob(os.path.join(workdir, '*.nc'))
        txtfiles = glob.glob(os.path.join(workdir, '*.txt'))
        allfiles = ncfiles + txtfiles
        for f in allfiles:
            shutil.move(f, os.path.join(outdir, os.path.basename(f)))
        # remove temp directory
        shutil.rmtree(workdir)
        # advance to the next cycle
        nowTime = nowTime + dt.timedelta(hours=assim_freq)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input YAML Configuration', required=True)
    args = parser.parse_args()
    # read YAML for config
    try:
        with open(args.config, 'r') as yaml_opened:
            config = yaml.safe_load(yaml_opened)
    except Exception as e:
        logging.error(f'Error occurred when attempting to load: {args.config}, error: {e}')

    run_satbias_conv(config)
