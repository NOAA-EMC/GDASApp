#!/usr/bin/env python3
from pathlib import Path
import logging
import xarray as xr
import copy
import woa_to_mom6  # try normal import (module must be on PYTHONPATH)



# Config for the yearly climatology
CONFIG = {
    # Source via built-in WOA23 downloader
    "download_woa23": True,
    "woa23_var": "temperature",      # temperature | salinity
    "woa23_resolution": "0.25",      # 0.25 | 1.00 | 5.00
    "woa23_period": "annual",        # annual | monthly
    "woa23_month": "",               # MM when monthly
    "woa23_outdir": "./woa23",

    # Grid
    "nlon": 2880,
    "nlat": 1440,
    "dlon": 0.25,
    "dlat": 0.25,
    "xbnds": [-180.0, 180.0],
    "ybnds": [-90.0, 90.0],

    # Variables (first used for horizontal, all used for vertical)
    "scalar_field": ["t_an", "t_sdo"],

    # Vertical interpolation
    "layer_file": "/home/gvernier/runs/std-dev/2025083118/gdas.ocean.t18z.inst.f009.nc",
    "vertical": True,

    # Outputs
    "output_mosaic": "/home/gvernier/wrk/fre-test/dst/ocean_mosaic.nc",
    "output_file": "woa_on_mom6.nc",
    "vert_output": "woa_on_mom6_layers.nc",

    # Remap weights file (annual climatology)
    "remap_file": "woa_to_mom6_weights_annual.nc"
}


# Config for the monthly climatology

def make_monthly_config(month):
    """
    Return a CONFIG-like dict for the given month.
    month may be an int (1-12) or a string like '01'..'12'.
    """
    # Normalize/validate month to MM
    if isinstance(month, int):
        if not 1 <= month <= 12:
            raise ValueError("month must be in 1..12")
        mm = f"{month:02d}"
    else:
        mm = str(month).zfill(2)
        if not mm.isdigit() or not 1 <= int(mm) <= 12:
            raise ValueError("month must be in 1..12 or 'MM'")

    cfg = copy.deepcopy(CONFIG)
    cfg.update({
        "woa23_period": "monthly",
        "woa23_month": mm,
        "output_file": f"woa_on_mom6_{mm}.nc",
        "vert_output": f"woa_on_mom6_layers_{mm}.nc",
        "scalar_field": ["t_an"],
        # Monthly climatology weights (shared by all months)
        "remap_file": "woa_to_mom6_weights_annual.nc"
    })
    return cfg


# Example: CONFIG_MONTHLY = make_monthly_config(1)

def run():
    # Create yearly climatology
    woa_to_mom6.main(CONFIG)
    quit()
    # Loop over months to create monthly climatologies
    for month in range(1, 13):
        cfg_monthly = make_monthly_config(month)
        woa_to_mom6.main(cfg_monthly)


if __name__ == "__main__":
    run()
