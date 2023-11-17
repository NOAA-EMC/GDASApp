import netCDF4 as nc
import numpy as np

INVALID = -1.0
# Cosmic background temperature. Taken from Mather,J.C. et. al., 1999, "Calibrator Design for the COBE
# Far-Infrared Absolute Spectrophotometer (FIRAS)"Astrophysical Journal, vol 512, pp 511-520
TSPACE = 2.7253


class ACCoeff:
    def __init__(self, sat_id='metop-c'):
        file_name = 'amsua_' + sat_id + '_v2.ACCoeff.nc'
        nc_file = nc.Dataset(file_name)
        self.n_FOVS = len(nc_file.dimensions['n_FOVs'])
        self.n_Channels = len(nc_file.dimensions['n_Channels'])
        self.A_earth = nc_file.variables['A_earth'][:]
        self.A_platform = nc_file.variables['A_platform'][:]
        self.A_space = nc_file.variables['A_space'][:]


def remove_ant_corr(AC, iFOV, T):
    # AC:             Structure containing the antenna correction coefficients for the sensor of interest.
    # iFOV:           The FOV index for a scanline of the sensor of interest.
    # T:              On input, this argument contains the brightness

    if iFOV < 1 or iFOV > AC.n_FOVS or len(T) != AC.n_Channels:
        return [INVALID] * len(T)
    iFOV = iFOV - 1
    T = AC.A_earth[:, iFOV] * T + AC.A_platform[:, iFOV] * T + AC.A_space[:, iFOV] * TSPACE
    return T


def apply_ant_corr(AC, iFOV, T):
    # T:              On input, this argument contains the antenna temperatures for the sensor channels.
    if iFOV < 1 or iFOV > AC.n_FOVS or len(T) != AC.n_Channels:
        return [INVALID] * len(T)
    iFOV = iFOV - 1
    T = (T - AC.A_space[:, iFOV] * TSPACE) / (AC.A_earth[:, iFOV] + AC.A_platform[:, iFOV])
    return T

