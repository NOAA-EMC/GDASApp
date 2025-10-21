#!/usr/bin/env python3
from pathlib import Path
import calendar
from datetime import datetime, timedelta
import xarray as xr
import numpy as np
import argparse

# Usage (positional still supported):
#   splice_clim.py YYYYMMDDHH [dir] [out.nc] [var]
# Options:
#   --layer-file PATH   # MOM6 layer file (thickness h)
#   --yearly FILE       # Yearly climatology on MOM6 layers
#   --depth-threshold M # Depth (m) for yearly replacement
#   --salinity-var NAME # Salinity variable name (default: Salt)
#   --refp PR           # Reference pressure (dbar) for theta


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=(
            "Time-interpolate monthly MOM6-layer climatologies, replace "
            "deep layers with yearly climatology, and convert in-situ "
            "temperature to potential temperature."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("date", help="Target datetime YYYYMMDDHH")
    p.add_argument(
        "dir", nargs="?", default=".",
        help="Directory with monthly files"
    )
    p.add_argument("out", nargs="?", default=None, help="Output file path")
    p.add_argument(
        "var", nargs="?", default="Temp",
        help="Variable to process (e.g., Temp)"
    )

    p.add_argument(
        "--layer-file", dest="layer_file", required=True,
        help="MOM6 layer thickness file (contains variable 'h')"
    )
    p.add_argument(
        "--yearly", dest="yearly", required=False,
        help="Yearly climatology file on MOM6 layers"
    )
    p.add_argument(
        "--depth-threshold", type=float, default=1400.0,
        help="Depth threshold (m) for yearly replacement"
    )
    p.add_argument(
        "--salinity-var", default="Salt",
        help="Salinity variable name for theta conversion"
    )
    p.add_argument(
        "--refp", type=float, default=0.0,
        help="Reference pressure (dbar) for potential temperature"
    )
    return p.parse_args(argv)


def compute_layer_centers(layer_file, layer_var="h"):
    """Compute layer-center depths (m, positive-down) from MOM6 layer file."""
    layer = xr.open_dataset(layer_file, decode_times=False)
    if layer_var not in layer:
        raise ValueError(f"Could not find '{layer_var}' in layer file")
    h = layer[layer_var].load()

    # Find z dimension name
    z_dim = None
    for d in h.dims:
        if d.lower().startswith("z"):
            z_dim = d
            break
    if z_dim is None:
        raise ValueError("Could not find z-dimension in layer file")

    # Cum-sum to interfaces, then centers; anchor surface to 0
    zw = xr.apply_ufunc(
        np.cumsum, h, input_core_dims=[[z_dim]], output_core_dims=[[z_dim]]
    )
    zc = zw - 0.5 * h
    zc = zc - zc.isel({z_dim: 0})

    # If a time dimension is present, take the first slice
    for d in zc.dims:
        if d.lower().startswith("time"):
            zc = zc.isel({d: 0})
            break
    return zc


def time_weights(dt):
    """Return (y1,m1, y2,m2, f1, f2) using mid-month anchoring around dt."""

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

    frac = (dt - mid1).total_seconds() / (mid2 - mid1).total_seconds()
    f1 = 1.0 - frac
    f2 = frac
    return (y1, m1, y2, m2, f1, f2)


def maybe_theta(T, S, depth_m, refp=0.0):
    """Convert in-situ T to potential temperature (theta), if possible.

    Inputs are xarray DataArrays; depth_m in meters (positive-down).
    Returns a DataArray (theta) or None on failure.
    """
    try:
        import importlib
        sw = importlib.import_module("seawater")  # provides ptmp(S, T, P, PR)
    except Exception:
        print(
            "⚠️  Optional package 'seawater' not available; skipping theta "
            "conversion"
        )
        return None

    P = depth_m.astype(np.float64).values
    Tv = T.astype(np.float64).values
    Sv = S.astype(np.float64).values
    try:
        theta_v = sw.ptmp(Sv, Tv, P, PR=refp)
    except Exception as e:
        print(f"⚠️  Potential temperature conversion failed: {e}")
        return None

    theta = xr.DataArray(
        theta_v,
        dims=T.dims,
        coords=T.coords,
        name=T.name,
        attrs=dict(T.attrs, long_name="potential temperature (theta)")
    )
    return theta


def main(argv=None):
    args = parse_args(argv)

    date_str = args.date
    base_dir = Path(args.dir)
    out_path = (
        Path(args.out)
        if args.out is not None
        else Path(f"woa_on_mom6_layers_{date_str}.nc")
    )
    var_name = args.var

    dt = datetime.strptime(date_str, "%Y%m%d%H")

    # Determine months and weights
    y1, m1, y2, m2, f1, f2 = time_weights(dt)

    p1 = base_dir / f"woa_on_mom6_layers_{m1:02d}.nc"
    p2 = base_dir / f"woa_on_mom6_layers_{m2:02d}.nc"

    ds1 = xr.open_dataset(p1)
    ds2 = xr.open_dataset(p2)

    # Interpolate only the requested variable (default: Temp)
    da = f1 * ds1[var_name] + f2 * ds2[var_name]

    # Depth centers from layer file (required)
    zc = compute_layer_centers(args.layer_file, layer_var="h")

    # Replace below depth threshold with yearly climatology if available
    if args.yearly:
        yearly_path = Path(args.yearly)
    else:
        yearly_path = base_dir / "woa_on_mom6_layers.nc"
    if yearly_path.exists():
        dsY = xr.open_dataset(yearly_path)
        if var_name in dsY:
            mask_deep = zc >= args.depth_threshold
            da_aligned, y_aligned = xr.align(da, dsY[var_name], join="exact")
            da = xr.where(mask_deep, y_aligned, da_aligned)
            print(
                f"📎 Replaced depths ≥ {args.depth_threshold} m with yearly"
            )
        else:
            print(
                f"⚠️  Yearly file missing variable {var_name}; skipping "
                "deep replacement"
            )
    else:
        print(
            f"⚠️  Yearly file not found: {yearly_path}; skipping deep "
            "replacement"
        )

    # Convert Temp to potential temperature, if possible
    converted_theta = False
    if var_name.lower().startswith("temp"):
        sal_name = args.salinity_var
        if (sal_name in ds1) and (sal_name in ds2):
            S = f1 * ds1[sal_name] + f2 * ds2[sal_name]
            if 'dsY' in locals() and sal_name in dsY:
                S = xr.where(zc >= args.depth_threshold, dsY[sal_name], S)
            theta = maybe_theta(da, S, zc, refp=args.refp)
            if theta is not None:
                da = theta
                converted_theta = True
                print(
                    "✅ Converted in-situ temperature to potential "
                    "temperature (theta)"
                )
        else:
            print(
                f"⚠️  Salinity variable '{sal_name}' not found in monthly "
                "files; skipping theta conversion"
            )

    out = xr.Dataset({var_name: da})
    out = out.assign_coords(ds1.coords)
    out.attrs.update({
        "source": (
            "Temporal interpolation of monthly climatology "
            "(midpoint-anchored)"
        ),
        "t_interp": date_str,
        "variable": var_name,
        "weights": (
            f"{f1:.6f} (M{m1:02d} mid) + {f2:.6f} (M{m2:02d} mid)"
        ),
        "depth_threshold": args.depth_threshold,
        "yearly_used": yearly_path.exists(),
        "theta_conversion": converted_theta,
        "ref_pressure_dbar": args.refp if converted_theta else None,
    })

    out.to_netcdf(out_path, format="NETCDF4_CLASSIC")


if __name__ == "__main__":
    main()
