#!/usr/bin/env python3
import sys
from pathlib import Path
import calendar
from datetime import datetime, timedelta
import xarray as xr

# Usage: splice_clim.py YYYYMMDDHH [dir] [out.nc] [var]
# Interpolates between monthly WOA climatologies on MOM6 layers.
# Expects files: woa_on_mom6_layers_MM.nc in dir.


def main():
    date_str = sys.argv[1]
    base_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    out_path = (
        Path(sys.argv[3]) if len(sys.argv) > 3
        else Path(f"woa_on_mom6_layers_{date_str}.nc")
    )
    var_name = sys.argv[4] if len(sys.argv) > 4 else "Temp"

    dt = datetime.strptime(date_str, "%Y%m%d%H")

    def month_midpoint(y, m):
        days = calendar.monthrange(y, m)[1]
        return datetime(y, m, 1) + timedelta(days=days / 2.0)

    def prev_month(y, m):
        return (y - 1, 12) if m == 1 else (y, m - 1)

    def next_month(y, m):
        return (y + 1, 1) if m == 12 else (y, m + 1)

    y, m = dt.year, dt.month
    mid_cur = month_midpoint(y, m)

    if dt >= mid_cur:
        y1, m1 = y, m
        y2, m2 = next_month(y, m)
        mid1 = mid_cur
        mid2 = month_midpoint(y2, m2)
    else:
        y2, m2 = y, m
        y1, m1 = prev_month(y, m)
        mid1 = month_midpoint(y1, m1)
        mid2 = mid_cur

    # Linear weights between midpoints
    frac = (dt - mid1).total_seconds() / (mid2 - mid1).total_seconds()
    f1 = 1.0 - frac
    f2 = frac

    p1 = base_dir / f"woa_on_mom6_layers_{m1:02d}.nc"
    p2 = base_dir / f"woa_on_mom6_layers_{m2:02d}.nc"

    ds1 = xr.open_dataset(p1)
    ds2 = xr.open_dataset(p2)

    # Interpolate only the requested variable (default: Temp)
    da = f1 * ds1[var_name] + f2 * ds2[var_name]
    out = xr.Dataset({var_name: da})

    out = out.assign_coords(ds1.coords)
    out.attrs.update({
        "source": (
            "Temporal interpolation of monthly climatology"
            " (midpoint-anchored)"
        ),
        "t_interp": date_str,
        "variable": var_name,
        "weights": (
            f"{f1:.6f} (M{m1:02d} mid) + {f2:.6f} (M{m2:02d} mid)"
        ),
    })

    out.to_netcdf(out_path, format="NETCDF4_CLASSIC")


if __name__ == "__main__":
    main()
