#!/usr/bin/env python3
#
# (C) Copyright 2021-2022 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# This file is copied from the JEDI ioda-converts repo.
#

import argparse
import numpy as np
import pandas as pd
import sys
from datetime import datetime, timezone
from dateutil.parser import parse

import pyiodaconv.ioda_conv_engines as iconv
from collections import defaultdict, OrderedDict
from pyiodaconv.orddicts import DefaultOrderedDict
from pyiodaconv.def_jedi_utils import epoch, iso8601_string
from pyiodaconv.def_jedi_utils import record_time

locationKeyList = [
    ("latitude", "float"),
    ("longitude", "float"),
    ("stationElevation", "float"),
    ("dateTime", "long"),
]

VarDims = {
    'totalSnowDepth': ['Location'],
}

float_missing_value = iconv.get_default_fill_val(np.float32)
int_missing_value = iconv.get_default_fill_val(np.int32)
long_missing_value = iconv.get_default_fill_val(np.int64)


def get_epoch_time(adatetime):

    # take python datetime object and convert to seconds from epoch
    time_offset = round((adatetime - epoch).total_seconds())

    return time_offset


class GHCNConverter(object):

    def __init__(self, filename, fixfile, date, warn):
        self.filename = filename
        self.fixfile = fixfile
        self.date = date
        self.warn = warn
        self.varDict = defaultdict(lambda: defaultdict(dict))
        self.metaDict = defaultdict(lambda: defaultdict(dict))
        self.outdata = defaultdict(lambda: DefaultOrderedDict(OrderedDict))
        self.varAttrs = defaultdict(lambda: DefaultOrderedDict(OrderedDict))
        self.AttrData = {}
        self.DimDict = {}
        self._read()

    def _read(self):

        # set up variable names for IODA
        iodavar = 'totalSnowDepth'
        self.varDict[iodavar]['valKey'] = iodavar, iconv.OvalName()
        self.varDict[iodavar]['errKey'] = iodavar, iconv.OerrName()
        self.varDict[iodavar]['qcKey'] = iodavar, iconv.OqcName()
        self.varAttrs[iodavar, iconv.OvalName()]['coordinates'] = 'longitude latitude'
        self.varAttrs[iodavar, iconv.OerrName()]['coordinates'] = 'longitude latitude'
        self.varAttrs[iodavar, iconv.OqcName()]['coordinates'] = 'longitude latitude'
        self.varAttrs[iodavar, iconv.OvalName()]['units'] = 'mm'
        self.varAttrs[iodavar, iconv.OerrName()]['units'] = 'mm'

        # read in the GHCN data csv file
        cols = ["ID", "DATETIME", "ELEMENT", "DATA_VALUE", "M_FLAG", "Q_FLAG", "S_FLAG", "OBS_TIME"]
        sub_cols = ["ID", "DATETIME", "ELEMENT", "DATA_VALUE"]
        df30_list = []
        # Fix dtypeWarning with mixed types via set low_memory=False
        df20all = pd.read_csv(self.filename, header=None, names=cols, low_memory=False)
        df20 = df20all[sub_cols]
        df20all = None
        df30_list.append(df20)
        df20 = None

        # select only snow depth, valid obs, and date
        df30 = pd.concat(df30_list, ignore_index=True)
        df30 = df30[df30["ELEMENT"] == "SNWD"]
        df30 = df30[df30["DATA_VALUE"].astype('float32') >= 0.0]
        df30["DATETIME"] = df30.apply(lambda row: parse(str(row["DATETIME"])).date(), axis=1)
        startdate = self.date
        valid_date = datetime.strptime(startdate, "%Y%m%d%H")
        valid_date = valid_date.replace(tzinfo=timezone.utc)
        select_date = valid_date.strftime('%Y%m%d')
        new_date = parse(select_date).date()
        df30 = df30[df30["DATETIME"] == new_date]

        # Read in the GHCN station files
        cols = ["ID", "LATITUDE", "LONGITUDE", "ELEVATION", "STATE", "NAME", "GSN_FLAG", "HCNCRN_FLAG", "WMO_ID"]
        df10all = pd.read_csv(self.fixfile, header=None, sep='\r\n', engine='python')
        df10all = df10all[0].str.split('\\s+', expand=True)
        df10 = df10all.iloc[:, 0:4]
        df10all = None
        sub_cols = {0: "ID", 1: "LATITUDE", 2: "LONGITUDE", 3: "ELEVATION"}
        df10 = df10.rename(columns=sub_cols)
        df10 = df10.drop_duplicates(subset=["ID"])

        # merge on ID to pull coordinates from the fix file
        df300 = pd.merge(df30, df10[['ID', 'LATITUDE', 'LONGITUDE', 'ELEVATION']], on='ID', how='left')

        # if merge (left) cannot find ID in df10, will insert NaN
        if any(df300['LATITUDE'].isna()):
            if (self.warn):
                print(f"\n WARNING: ignoring ghcn stations missing from station_list")
            else:
                sys.exit(f"\n ERROR: ghcn data files contains station not in station_list.")

        sites = df300["ID"].values
        vals = df300["DATA_VALUE"].values
        lats = df300["LATITUDE"].values
        lons = df300["LONGITUDE"].values
        alts = df300["ELEVATION"].values

        vals = vals.astype('float32')
        lats = lats.astype('float32')
        lons = lons.astype('float32')
        alts = alts.astype('float32')

        # set qflg to 0 (do we need this?), error to 40.
        qflg = np.full(vals.shape, 0, dtype='int32')
        errs = np.full(vals.shape, 40.0, dtype='float32')

        # get datetime from input
        my_date = datetime.strptime(startdate, "%Y%m%d%H")
        my_date = my_date.replace(tzinfo=timezone.utc)
        epoch_time = np.int64(get_epoch_time(my_date))

        times = np.full(vals.shape, epoch_time, dtype='int64')

        # add metadata variables
        self.outdata[('dateTime', 'MetaData')] = times
        self.outdata[('stationIdentification', 'MetaData')] = sites
        self.outdata[('latitude', 'MetaData')] = lats
        self.outdata[('longitude', 'MetaData')] = lons
        self.outdata[('stationElevation', 'MetaData')] = alts
        self.varAttrs[('stationElevation', 'MetaData')]['units'] = 'm'
        self.varAttrs[('dateTime', 'MetaData')]['units'] = iso8601_string
        self.varAttrs[('dateTime', 'MetaData')]['_FillValue'] = long_missing_value

        self.outdata[self.varDict[iodavar]['valKey']] = vals
        self.outdata[self.varDict[iodavar]['errKey']] = errs
        self.outdata[self.varDict[iodavar]['qcKey']] = qflg

        self.DimDict['Location'] = len(self.outdata[('dateTime', 'MetaData')])


def main():

    parser = argparse.ArgumentParser(
        description=('Read GHCN snow depth file(s) and Converter'
                     ' of native csv format for observations of snow'
                     ' depth from GHCN to IODA netCDF format.')
    )
    parser.add_argument('-i', '--input',
                        help="name of ghcn snow depth input file(s)",
                        type=str, required=True)
    parser.add_argument('-f', '--fixfile',
                        help="name of ghcn station fixed file(s)",
                        type=str, required=True)
    parser.add_argument('-o', '--output',
                        help="name of ioda output file",
                        type=str, required=True)
    parser.add_argument('-d', '--date',
                        help="base date (YYYYMMDDHH)", type=str, required=True)
    parser.add_argument('--warn_on_missing_stn',
                        help="if present: missing stations in the fix file will warn, rather than exit",
                        action='store_true')

    args = parser.parse_args()

    # start timer
    tic = record_time()

    # Read in the GHCN snow depth data
    snod = GHCNConverter(args.input, args.fixfile, args.date, args.warn_on_missing_stn)

    writer = iconv.IodaWriter(args.output, locationKeyList, snod.DimDict)

    writer.BuildIoda(
        snod.outdata,
        VarDims,
        snod.varAttrs,
        snod.AttrData
    )

    # report time
    toc = record_time(tic=tic)


if __name__ == '__main__':
    main()
