#!/usr/bin/env python3
from pathlib import Path
import calendar
from datetime import datetime, timedelta
import xarray as xr
import numpy as np
import argparse
import gsw


# Usage:
#   splice_clim.py --date YYYYMMDDHH [--dir DIR] [--out FILE]
#                  --layer-file PATH [--yearly FILE]
#                  [--depth-threshold M] [--refp PR]
# Description:
#   Interpolates monthly MOM6-layer climatologies for Temp and Salt,
#   replaces deep layers with yearly climatology, and converts Temp to
#   potential temperature using TEOS-10 (gsw).


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=(
            "Time-interpolate monthly MOM6-layer climatologies for Temp and "
            "Salt, replace deep layers with yearly climatology, and convert "
            "Temp (in-situ) to potential temperature."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--date", required=True, help="Target datetime YYYYMMDDHH"
    )
    p.add_argument(
        "--dir", default=".", help="Directory with monthly files"
    )
    p.add_argument(
        "--out", default=None, help="Output file path"
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

    # Integrate thickness to get interfaces, then centers; anchor surface to 0
    # Use xarray's cumsum to preserve dimension structure
    zw = h.cumsum(dim=z_dim)
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


def convert_to_potential(T, S, depth_m, refp=0.0):
    """Convert in-situ T to potential temperature (theta) using gsw.

    Note: assumes provided salinity is close to Absolute Salinity (SA).
    """
    p = depth_m.astype(np.float64).values  # approx: 1 dbar ≈ 1 m
    Tv = T.astype(np.float64).values
    Sv = S.astype(np.float64).values  # treating as SA for simplicity
    try:
        theta_v = gsw.pt_from_t(Sv, Tv, p, refp)
    except Exception as e:
        print(
            f"⚠️  Potential temperature conversion (gsw.pt_from_t) failed: {e}"
        )
        return None
    theta = xr.DataArray(
        theta_v,
        dims=T.dims,
        coords=T.coords,
        name=T.name,
        attrs=dict(T.attrs, long_name="potential temperature (theta)")
    )
    return theta


def drop_time_dim(da: xr.DataArray) -> xr.DataArray:
    """Drop a degenerate time dimension (size=1) if present."""
    for d in list(da.dims):
        if d.lower().startswith("time") and da.sizes[d] == 1:
            da = da.isel({d: 0}, drop=True)
    return da


def main(argv=None):
    args = parse_args(argv)

    date_str = args.date
    base_dir = Path(args.dir)
    out_path = (
        Path(args.out) if args.out is not None
        else Path(f"woa_on_mom6_layers_{date_str}.nc")
    )

    dt = datetime.strptime(date_str, "%Y%m%d%H")

    # Determine months and weights
    y1, m1, y2, m2, f1, f2 = time_weights(dt)

    p1 = base_dir / f"woa_on_mom6_layers_{m1:02d}.nc"
    p2 = base_dir / f"woa_on_mom6_layers_{m2:02d}.nc"

    ds1 = xr.open_dataset(p1)
    ds2 = xr.open_dataset(p2)

    # Ensure variables exist
    for v in ("Temp", "Salt"):
        if v not in ds1 or v not in ds2:
            raise RuntimeError(
                f"Missing variable '{v}' in monthly files {p1} or {p2}"
            )

    # Capture degenerate time dimension info (if present)
    time_dim_name = None
    time_values = None
    for d in ds1["Temp"].dims:
        if d.lower().startswith("time") and ds1["Temp"].sizes[d] == 1:
            time_dim_name = d
            if d in ds1:
                time_values = ds1[d].values
            elif d in ds1.coords:
                time_values = ds1.coords[d].values
            else:
                time_values = None
            break

    # Interpolate variables
    temp = f1 * ds1["Temp"] + f2 * ds2["Temp"]
    salt = f1 * ds1["Salt"] + f2 * ds2["Salt"]

    # Drop degenerate time dimension (expected size=1)
    temp = drop_time_dim(temp)
    salt = drop_time_dim(salt)

    # Depth centers from layer file (required)
    zc = compute_layer_centers(args.layer_file, layer_var="h")

    # Replace below depth threshold with yearly climatology (mandatory)
    if args.yearly:
        yearly_path = Path(args.yearly)
    else:
        yearly_path = base_dir / "woa_on_mom6_layers.nc"
    if not yearly_path.exists():
        raise RuntimeError(
            f"Yearly file not found (required for deep replacement): "
            f"{yearly_path}"
        )

    dsY = xr.open_dataset(yearly_path)
    missing_y = [v for v in ("Temp", "Salt") if v not in dsY]
    if missing_y:
        raise RuntimeError(
            "Yearly file missing required variable(s): "
            + ", ".join(missing_y)
        )

    # Build explicit 3D boolean mask (z,y,x) from depth centers
    # Expect zc to have identical dims/sizes as the monthly fields
    if zc.dims != temp.dims or any(
        zc.sizes[d] != temp.sizes[d] for d in temp.dims
    ):
        msg = (
            "Layer depth grid (zc) must have same dims/sizes as fields.\n"
            f"zc.dims={zc.dims}, zc.sizes={dict(zc.sizes)}\n"
            f"field.dims={temp.dims}, field.sizes={dict(temp.sizes)}"
        )
        raise RuntimeError(msg)
    mask3d = xr.DataArray(
        (zc >= args.depth_threshold).values,
        dims=temp.dims,
        coords=temp.coords,
        name="deep_mask",
    )

    # Yearly fields (must have identical structure to monthly fields)
    yT = drop_time_dim(dsY["Temp"])
    yS = drop_time_dim(dsY["Salt"])
    if yT.dims != temp.dims or any(
        yT.sizes[d] != temp.sizes[d] for d in temp.dims
    ):
        msg = (
            "Yearly Temp dims/sizes do not match monthly Temp.\n"
            f"yearly.dims={yT.dims}, yearly.sizes={dict(yT.sizes)}\n"
            f"monthly.dims={temp.dims}, monthly.sizes={dict(temp.sizes)}"
        )
        raise RuntimeError(msg)
    if yS.dims != salt.dims or any(
        yS.sizes[d] != salt.sizes[d] for d in salt.dims
    ):
        msg = (
            "Yearly Salt dims/sizes do not match monthly Salt.\n"
            f"yearly.dims={yS.dims}, yearly.sizes={dict(yS.sizes)}\n"
            f"monthly.dims={salt.dims}, monthly.sizes={dict(salt.sizes)}"
        )
        raise RuntimeError(msg)

    # Direct replacement in deep ocean using 3D mask
    temp = xr.where(mask3d, yT, temp)
    salt = xr.where(mask3d, yS, salt)
    print(
        f"📎 Replaced depths ≥ {args.depth_threshold} m with yearly"
    )

    # Convert Temp (in-situ) to potential temperature using Salt
    theta = convert_to_potential(temp, salt, zc, refp=args.refp)
    if theta is not None:
        temp = theta
        converted_theta = True
    else:
        converted_theta = False

    out = xr.Dataset({"Temp": temp, "Salt": salt})
    # Add back a size-1 time dimension if present in inputs
    if time_dim_name is not None:
        out = out.expand_dims({
            time_dim_name: time_values if time_values is not None else [0]
        })

    out.attrs.update({
        "source": (
            "Temporal interpolation of monthly climatology "
            "(midpoint-anchored)"
        ),
        "t_interp": date_str,
        "variables": "Temp,Salt",
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
