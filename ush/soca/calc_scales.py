#!/usr/bin/env python
# TODO: Copied/pasted from SOCA, point to the original one after we update the JEDI #

import netCDF4 as nc
import numpy as np
import warnings
from scipy.ndimage import gaussian_filter, distance_transform_edt
import yaml
import argparse


def load_config(config_file):
    with open(config_file, 'r') as stream:
        config = yaml.safe_load(stream)
    return config


def run(yaml_file):
    config = load_config(yaml_file)
    gridspec_filename = config.get('gridspec_filename', "./soca_gridspec.nc")
    restart_filename = config.get('restart_filename', "./MOM.res.nc")
    mld_filename = config.get('mld_filename', "./average_MLD.nc")
    output_filename = config.get('output_filename', "./scales.nc")
    output_variable_vt = config.get('output_variable_vt', 'vt')
    output_variable_hz = config.get('output_variable_hz', 'hz')

    VT_MIN = float(config.get('VT_MIN', 1.5))
    VT_MAX = float(config.get('VT_MAX', 10))

    HZ_ROSSBY_MULT = float(config.get('HZ_ROSSBY_MULT', 1.0))
    HZ_MAX = float(config.get('HZ_MAX', 200e3))
    HZ_MIN_GRID_MULT = float(config.get('HZ_MIN_GRID_MULT', 1.0))

    # read input
    with nc.Dataset(gridspec_filename, 'r') as src:
        rossbyRadius = src.variables['rossby_radius'][0]
        dx = src.variables['dx'][0]
        dy = src.variables['dy'][0]
        area = src.variables['area'][0]
        mask = src.variables['mask2d'][0]
    with nc.Dataset(restart_filename, 'r') as src:
        h = src.variables['h'][0]
        varType = src.variables['h'].datatype
    with nc.Dataset(mld_filename, 'r') as src:
        mld = src.variables['MLD'][0]
    nz = h.shape[0]

    # calculate horizontal scales
    hz_scales = rossbyRadius * HZ_ROSSBY_MULT
    hz_scales = np.clip(hz_scales, a_min=dx*HZ_MIN_GRID_MULT, a_max=HZ_MAX)
    hz_scales = np.clip(hz_scales, a_min=dy*HZ_MIN_GRID_MULT, a_max=HZ_MAX)

    # calculate hz smoothing scales for use inside this script.
    # The scales (in units of # of grid cells) is zonally averaged, we assume hz scales
    # do not vary as much with longitude as they do with latitude
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        smoothingScale = np.nanmean(np.where(mask, hz_scales/np.sqrt(area), np.NaN), axis=1)
    smoothingScale[0] = smoothingScale[1]
    smoothingScale[-1] = smoothingScale[-2]

    # smooth the horizontal scales WITH the horizontal scales.
    hz_scales_orig = hz_scales.copy()
    for j in range(hz_scales.shape[0]):  # zonally for efficiency (otherwise it would be am i/j set of for loops)
        hz_scales[j, :] = gaussian_filter(hz_scales_orig, sigma=smoothingScale[j], mode='nearest')[j, :]
    hz_scales = np.where(mask, hz_scales, 0)
    del hz_scales_orig

    # calculate vertical scales.
    # ---------------------------------------------------------

    # initialize with zeros
    vtScales = np.zeros_like(h)

    # smooth the MLD with the horizontal scales.
    mld_orig = mld.copy()
    # fill missing
    mld_orig = mld[tuple(distance_transform_edt(mask == 0, return_distances=False, return_indices=True))]
    for j in range(mld.shape[0]):  # zonally for efficiency (otherwise it would be am i/j set of for loops)
        mld[j, :] = gaussian_filter(mld_orig, sigma=smoothingScale[j], mode='nearest')[j, :]
    mld = np.where(mask, mld, 0)
    del mld_orig

    # calculate layer depths for use later
    layerDepth = np.cumsum(h, axis=0) - h/2.0
    maxLevels = np.sum(np.where(h > 0.01, 1, 0), axis=0)  # number of lvls before we hit bottom

    # find index of last level in the mixed layer
    mlLastLevel = np.where(layerDepth < np.stack([mld]*nz, axis=0), 1, 0)
    mlLastLevel[h <= 0.01] = 0  # don't count small bottom layers
    mlLastLevel = np.clip(np.sum(mlLastLevel, axis=0)-1, a_min=0, a_max=nz-2)

    # add to that a fraction of layer at the bottom of the mixed layer
    # for a total fractional number of levels in the ML
    y_idx, x_idx = np.indices(mlLastLevel.shape)
    depth1 = layerDepth[mlLastLevel, y_idx, x_idx]
    depth2 = layerDepth[mlLastLevel+1, y_idx, x_idx]
    mlLayers = mlLastLevel + (mld - depth1) / (depth2-depth1)
    mlLayers = np.clip(mlLayers, a_min=1, a_max=maxLevels)

    # set the top to the number of levels in the ML, interpolate down to bottom of ML
    # AND enforce a min/max value. The max value is important in order
    # to keep the number of diffusion iterations in check. The resulting diracs
    # are not quite the same... but close enough.
    layer, _, _ = np.indices(h.shape)
    mlLayers3D = np.stack([mlLayers]*nz, axis=0)
    vtScales[:] = np.clip(mlLayers3D - layer, a_min=VT_MIN, a_max=VT_MAX)

    # ignore thin layers at the bottom
    vtScales[h <= 0.01] = 0

    # write output file
    with nc.Dataset(output_filename, 'w') as dst:
        dst.createDimension('Time', None)
        dst.createDimension('z', vtScales.shape[0])
        dst.createDimension('y', vtScales.shape[1])
        dst.createDimension('x', vtScales.shape[2])

        time = dst.createVariable('Time', varType, ('Time',))
        var_vt = dst.createVariable(output_variable_vt, varType, ('z', 'y', 'x'))
        var_hz = dst.createVariable(output_variable_hz, varType, ('y', 'x'))

        var_vt[:] = vtScales
        var_hz[:] = hz_scales


def main():
    parser = argparse.ArgumentParser(description='Process some netCDF files.')
    parser.add_argument('config_file', help='Path to the YAML configuration file')
    args = parser.parse_args()

    run(args.config_file)


if __name__ == "__main__":
    main()
