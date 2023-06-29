#!/usr/bin/env python3
# diag_statistics.py
# in ocnanalvrfy task, untar and unzip ocean-relevant diag files from
# atmospheric analysis, calculate means, and write them as ascii to arcdir
import os
import numpy as np
import pandas as pd
from netCDF4 import Dataset
import tarfile
import gzip
import shutil

variables = ['sst', 't']

data = os.getenv('DATA')
pdy = os.getenv('PDY')
cyc = os.getenv('cyc')
comout = os.getenv('COM_ATMOS_ANALYSIS')
arcdir = os.getenv('ARCDIR')


def get_diag_stats():

    tarfilename = 'gdas.t' + cyc + 'z.cnvstat'

    os.chdir(data)

    for var in variables:

        diagfilename = 'diag_conv_' + var + '_ges.' + pdy + cyc + '.nc4'
        zipfilename = diagfilename + '.gz'
        outfilename = 'cnvstat.' + var + '.gdas.' + pdy + cyc + '.csv'

        try:
            with tarfile.open(os.path.join(comout, tarfilename), "r") as tf:
                tf.extract(member=zipfilename)
        except FileNotFoundError:
            print('WARNING: file', os.path.join(comout, tarfilename),
                  'not found, this is expected in GDASApp ctests')
            return
        with gzip.open(zipfilename, 'rb') as f_in:
            with open(diagfilename, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # The following is lifted from PyGSI/src/pyGSI/diags.py

        df_dict = {}

        # Open netCDF file, store data into dictionary
        with Dataset(diagfilename, mode='r') as f:
            for var in f.variables:
                # Station_ID and Observation_Class variables need
                # to be converted from byte string to string
                if var in ['Station_ID', 'Observation_Class']:
                    diagdata = f.variables[var][:]
                    diagdata = [i.tobytes(fill_value='/////', order='C')
                                for i in diagdata]
                    diagdata = np.array(
                        [''.join(i.decode('UTF-8', 'ignore').split())
                         for i in diagdata])
                    df_dict[var] = diagdata

                # Grab variables with only 'nobs' dimension
                elif len(f.variables[var].shape) == 1:
                    df_dict[var] = f.variables[var][:]

        # Create pandas dataframe from dict
        df = pd.DataFrame(df_dict)

        # looking at the used observations, maybe variations on this later
        df = df[df.Analysis_Use_Flag == 1.0]

        # this is a crude filter to obtain surface t observations, hopefully
        # catching at least most of the airborn observations and passing the
        # sea observations (with much else)
        # TODO: This needs to be refined, possibly using obtype
        df = df[df.Station_Elevation <= 10.0]

        meaned_cols = ['Obs_Minus_Forecast_unadjusted',
                       'Obs_Minus_Forecast_adjusted']

        df[meaned_cols] = np.abs(df[meaned_cols])

        means = df.groupby(['Observation_Type'])[meaned_cols].mean()
        mean_all = df[meaned_cols].mean()
        mean_all.name = 'All'
        means = pd.concat([means, mean_all.to_frame().T])
        means.index.name = 'obtype'

        outfilenamepath = os.path.join(arcdir, outfilename)
        print('writing ', outfilenamepath)
        means.to_csv(outfilenamepath)
