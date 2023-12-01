import netCDF4 as nc
import os
import numpy as np

INVALID = -1.0
# Cosmic background temperature. Taken from Mather,J.C. et. al., 1999, "Calibrator Design for the COBE
# Far-Infrared Absolute Spectrophotometer (FIRAS)"Astrophysical Journal, vol 512, pp 511-520
TSPACE = 2.7253


class ACCoeff:
    def __init__(self, ac_dir, sat_id='metop-c'):
        file_name = os.path.join(ac_dir, 'amsua_' + sat_id + '_v2.ACCoeff.nc')
        nc_file = nc.Dataset(file_name)
        self.n_fovs = len(nc_file.dimensions['n_FOVs'])
        self.n_channels = len(nc_file.dimensions['n_Channels'])
        self.a_earth = nc_file.variables['A_earth'][:]
        self.a_platform = nc_file.variables['A_platform'][:]
        self.a_space = nc_file.variables['A_space'][:]
        self.a_ep = self.a_earth + self.a_platform
        self.a_sp = self.a_space * TSPACE


def remove_ant_corr(i, ac, ifov, t):
    # AC:             Structure containing the antenna correction coefficients for the sensor of interest.
    # iFOV:           The FOV index for a scanline of the sensor of interest.
    # T:              On input, this argument contains the brightness
    t = ac.a_ep[i, ifov] * t + ac.a_sp[i, ifov]
    t[(ifov < 1) | (ifov > ac.n_fovs)] = [INVALID]
    return t


def apply_ant_corr(i, ac, ifov, t):
    # t:              on input, this argument contains the antenna temperatures for the sensor channels.
    t = (t - ac.a_sp[i, ifov]) / ac.a_ep[i, ifov]
    t[(ifov < 1) | (ifov > ac.n_fovs)] = [INVALID]
    return t
