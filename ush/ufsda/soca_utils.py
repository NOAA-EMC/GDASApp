import xarray
import glob
import numpy as np
import sys
import os
import logging
import shutil

# TODO: We might want to revisit this in the future
# Try to resolve the location of pyioda, assuming there are only 2 places where this
# script can exist (build/ush/ufsda or /ush/ufsda)
from pathlib import Path
jedilib = Path(os.path.join(Path(__file__).parent.absolute(), '../..', 'lib'))
if not jedilib.is_dir():
    jedilib = Path(os.path.join(Path(__file__).parent.absolute(), '../../build', 'lib'))
pyver = 'python3.'+str(sys.version_info[1])
pyioda_lib = Path(os.path.join(jedilib, pyver, 'pyioda')).resolve()
pyiodaconv_lib = Path(os.path.join(jedilib, 'pyiodaconv')).resolve()
sys.path.append(str(pyioda_lib))
sys.path.append(str(pyiodaconv_lib))
import pyiodaconv.ioda_conv_engines as iconv
from orddicts import DefaultOrderedDict

__all__ = ['concatenate_ioda']

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                    level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

marine_obs_names = ['seaSurfaceTemperature',
                    'absoluteDynamicTopography',
                    'seaIceFraction',
                    'seaIceFreeboard',
                    'waterTemperature',
                    'salinity',
                    'seaSurfaceSalinity']

iodatypes = {"ObsError": 'float32',
             "ObsValue": 'float32',
             "PreQC": 'int32'}


def obs_specs(iodafname):
    with xarray.open_dataset(iodafname, group='MetaData', decode_cf=False) as ds:
        timeref = ds['dateTime'].attrs['units']

    with xarray.open_dataset(iodafname, group='ObsValue') as ds:
        for varname in ds.variables:
            if varname in marine_obs_names:
                logging.info(f"Found {varname} in {iodafname}.")
                var = ds[varname]
                return varname, var.attrs['units'], timeref

    raise Exception(f"No known obs type in {iodafname}.")


def concatenate_ioda(iodafname):
    flist = glob.glob(iodafname+'.*')
    flist.sort()
    nfiles = len(flist)
    if nfiles == 0:
        logging.info(f"No files to concatenate.")
        return

    if len(flist) == 1:
        logging.info(f"Only file is {flist[0]}, rename to {iodafname}. No need to concatenate.")
        shutil.move(flist[0], iodafname)
        return

    logging.info(f"Concatenating {nfiles} files from globbing {iodafname}.*")

    # Identify variable and unit
    obsvarname, units, timeref = obs_specs(flist[0])

    # Concatenate stuff outside of groups (Location dimensions and variables)
    ds = xarray.concat([xarray.open_dataset(f) for f in flist], dim='Location')

    # Concatenate all groups except MetaData
    outdata = {}
    for group in ["ObsError", "ObsValue", "PreQC"]:
        ds = xarray.concat([xarray.open_dataset(f, group=group) for f in flist], dim='Location')
        outdata[(obsvarname, group)] = ds[obsvarname].astype(iodatypes[group])

    # Concatenate metadata
    ds = xarray.concat([xarray.open_dataset(f, group="MetaData", decode_cf=False) for f in flist], dim='Location')
    for k in list(ds.keys()):
        outdata[(k, "MetaData")] = ds[k]

    # Setup the IODA writer
    varattrs = DefaultOrderedDict(lambda: DefaultOrderedDict(dict))

    # obs attributes
    varattrs[(obsvarname, "ObsValue")]['units'] = units
    varattrs[(obsvarname, "ObsError")]['units'] = units

    # meta data attributes
    varattrs[('latitude', 'MetaData')]['units'] = 'degrees_north'
    varattrs[('longitude', 'MetaData')]['units'] = 'degrees_east'
    varattrs[('dateTime', 'MetaData')]['units'] = timeref
    locationkeylist = [("latitude", "float", "degrees_north"),
                       ("longitude", "float", "degrees_east"),
                       ("dateTime", "long", timeref)]

    vardims = {'': ['Location']}
    nlocs = ds.dims['Location']
    dimdict = {}
    dimdict['Location'] = nlocs
    globalattrs = {}

    # Write
    writer = iconv.IodaWriter(iodafname, locationkeylist, dimdict)
    writer.BuildIoda(outdata, vardims, varattrs, globalattrs)

    return
