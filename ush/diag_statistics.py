#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
from netCDF4 import Dataset

data = os.getenv('DATA')
pdy = os.getenv('PDY')
cyc = os.getenv('cyc')
comout = os.getenv('COM_ATMOS_ANALYSIS')
arcdir = os.getenv('ARCDIR')


def get_diag_stats():

    variables = ['sst', 't']

    tarfilename = 'gdas.t' + cyc + 'z.cnvstat'
    tarfile = os.path.join(comout, tarfilename)

    os.chdir(data)

    for var in variables:

        diagfilename = 'diag_conv_' + var + '_ges.' + pdy + cyc + '.nc4'
        diagfile = os.path.join(data, diagfilename)
        zipfilename = diagfilename + '.gz'
        zipfile = os.path.join(data, zipfilename)
        outfile = 'cnvstat.' + var + '.gdas.' + pdy + cyc

        # TODO: these probably should be in the jjob. Will try to get them there
        # once this is up and running
        command = 'tar -xvf ' + tarfile + ' ' + zipfilename
        print('running', command)
        os.system(command)
        command = 'gunzip ' + os.path.join(data, zipfile)
        print('running', command)
        os.system(command)

        # The following is lifted from PyGSI/src/pyGSI/diags.py

        df_dict = {}

        # Open netCDF file, store data into dictionary
        with Dataset(diagfile, mode='r') as f:
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

        print('writing ', outfile)
        means.to_csv(os.path.join(arcdir, outfile))

