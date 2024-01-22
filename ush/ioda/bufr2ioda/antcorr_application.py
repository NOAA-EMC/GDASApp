import netCDF4 as nc
import os
import numpy as np

R1000 = 1000.0
R1000000 = 1000000.0
INVALID = R1000
# Cosmic background temperature. Taken from Mather,J.C. et. al., 1999, "Calibrator Design for the COBE
# Far-Infrared Absolute Spectrophotometer (FIRAS)"Astrophysical Journal, vol 512, pp 511-520
TSPACE = 2.7253


class ACCoeff:
    def __init__(self, ac_dir, sat_id='n19'):
        file_name = os.path.join(ac_dir, 'amsua_' + sat_id + '.ACCoeff.nc')
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

    # print(f't before corr: {t[:100]}')
    t = ac.a_ep[i, ifov] * t + ac.a_sp[i, ifov]
    # print(f't after corr: {t[:100]}')
    t[(ifov < 1) | (ifov > ac.n_fovs)] = [INVALID]
    return t


def apply_ant_corr(i, ac, ifov, t):
    # t:              on input, this argument contains the antenna temperatures for the sensor channels.
    t = (t - ac.a_sp[i, ifov]) / ac.a_ep[i, ifov]
    t[(ifov < 1) | (ifov > ac.n_fovs)] = [INVALID]
    return t
