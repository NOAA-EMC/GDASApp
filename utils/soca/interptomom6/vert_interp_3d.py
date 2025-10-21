#!/usr/bin/env python3
import xarray as xr
import numpy as np
import sys
import argparse
import time
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from functools import partial
import os


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Vertically interpolate WOA data onto MOM6 layer coordinates"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s\n"
            "  %(prog)s -w in.nc -o out.nc\n"
            "  %(prog)s -l layers.nc -j 8\n"
        ),
    )

    parser.add_argument(
        '-w', '--woa-file',
        default="WOA18_on_MOM6.nc",
        help='Horizontally interpolated WOA file'
    )

    parser.add_argument(
        '-l', '--layer-file',
        default="./dst/MOM6_layer_h.nc",
        help='File with MOM6 layer thicknesses h(z,y,x)'
    )

    parser.add_argument(
        '-o', '--output-file',
        default="WOA18_on_MOM6_layers.nc",
        help='Output file for vertically interpolated data'
    )

    # Accept one or more variables (option can be repeated)
    parser.add_argument(
        '-v', '--variable', dest='variables', action='append', nargs='+',
        help=(
            'Variable name(s) to interpolate. May be repeated or '
            'comma-separated (e.g., -v t_an s_an  -v u_an,v_an  -v t_an,s_an)'
        )
    )

    parser.add_argument(
        '--depth-var',
        default="depth",
        help='Depth variable name in WOA file'
    )

    parser.add_argument(
        '--layer-var',
        default="h",
        help='Layer thickness variable name'
    )

    parser.add_argument(
        '--no-debug',
        action='store_true',
        help='Disable debug output for first few profiles'
    )

    parser.add_argument(
        '-j', '--jobs',
        type=int,
        default=cpu_count(),
        help='Number of parallel processes'
    )

    return parser.parse_args()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def interpolate_latitude_strip(args_tuple):
    """
    Interpolate a latitude strip in parallel - more efficient approach.

    Parameters:
    args_tuple: tuple containing
        (j_start, j_end, zc_strip, Tsrc_strip, depth_src)
    """
    (j_start, j_end, zc_strip, Tsrc_strip, depth_src) = args_tuple

    # Get dimensions
    nz, ny_strip, nx = zc_strip.shape[1:]  # Skip time dimension

    # Initialize result array for this strip
    result_strip = np.full_like(zc_strip, np.nan)

    # Process each profile in the strip
    for j_local in range(ny_strip):
        for i in range(nx):
            # Extract profiles for this location (time=0)
            prof_z = zc_strip[0, :, j_local, i]
            prof_T_src = Tsrc_strip[0, :, j_local, i]

            # Skip if depths are invalid
            if np.any(np.isnan(prof_z)) or np.all(prof_z == 0):
                continue  # already NaN

            # Interpolate
            prof_T_interp = np.interp(
                prof_z, depth_src, prof_T_src,
                left=np.nan, right=np.nan
            )
            result_strip[0, :, j_local, i] = prof_T_interp

    return (j_start, j_end, result_strip)


def mapped_name(var_name, existing):
    """Map WOA variable names to output names.

    Any name starting with 't_' -> 'Temp'; 's_' -> 'Salt'. If the mapped
    name already exists in the output set, append a suffix derived from the
    original variable to avoid collisions.
    """
    if var_name.startswith("t_"):
        base = "Temp"
    elif var_name.startswith("s_"):
        base = "Salt"
    else:
        return var_name

    new_name = base
    if new_name in existing:
        suffix = var_name.split("_", 1)[1] if "_" in var_name else var_name
        candidate = f"{base}_{suffix}"
        idx = 1
        while candidate in existing:
            candidate = f"{base}_{suffix}_{idx}"
            idx += 1
        new_name = candidate
    return new_name


# ---------------------------------------------------------------------
# 1️⃣ Parse arguments and setup
# ---------------------------------------------------------------------
args = parse_arguments()
woa_file = args.woa_file
layer_file = args.layer_file
out_file = args.output_file

# Build variables list supporting repeated flags and comma-separated lists
_variables_raw = args.variables if args.variables is not None else [["t_an"]]
_tokens = []
for _group in _variables_raw:
    for _item in _group:
        for _tok in _item.split(','):
            _tok = _tok.strip()
            if _tok:
                _tokens.append(_tok)
# Deduplicate preserving order
_seen = set()
variables = []
for _v in _tokens:
    if _v not in _seen:
        _seen.add(_v)
        variables.append(_v)

depth_var = args.depth_var
layer_var = args.layer_var
show_debug = not args.no_debug
num_jobs = args.jobs

# Show configuration
print("🌊 Vertical Interpolation: WOA → MOM6 Layers")
print("=" * 45)
print(f"WOA file:         {woa_file}")
print(f"Layer file:       {layer_file}")
print(f"Output file:      {out_file}")
print(f"Variables:        {', '.join(variables)}")
print(f"Depth variable:   {depth_var}")
print(f"Layer variable:   {layer_var}")
print(f"Parallel jobs:    {num_jobs}")
print("")

# ---------------------------------------------------------------------
# 2️⃣ Open datasets safely
# ---------------------------------------------------------------------
print(f"📥 Reading {woa_file} and {layer_file}")
start_time = time.time()
data_load_start = time.time()
try:
    woa = xr.open_dataset(woa_file, decode_times=False)
    layer = xr.open_dataset(layer_file, decode_times=False)
except Exception as e:
    sys.exit(f"❌ Failed to open one of the input files: {e}")
ldata = time.time() - data_load_start
print(f"⏱️  Data loading took {ldata:.2f}s")

# ---------------------------------------------------------------------
# 3️⃣ Get source and target vertical coordinates
# ---------------------------------------------------------------------
coord_setup_start = time.time()
if depth_var not in woa:
    sys.exit(f"❌ Could not find '{depth_var}' in WOA file.")

depth_src = woa[depth_var].values.astype(np.float64)

# Validate requested variables exist
missing = [v for v in variables if v not in woa]
if missing:
    msg = ", ".join(missing)
    sys.exit(f"❌ Missing variable(s) in WOA file: {msg}")

if layer_var not in layer:
    sys.exit(f"❌ Could not find '{layer_var}' in layer file.")
h = layer[layer_var].load()  # (z, y, x) or (time, z, y, x)

# compute depth edges and centers
# Find the z-dimension
z_dim = None
for dim in h.dims:
    if dim.lower().startswith('z'):
        z_dim = dim
        break

if z_dim is None:
    sys.exit("❌ Could not find z-dimension in layer thickness file.")

print(f"Layer thickness h: shape={h.shape}, z_dim={z_dim}")
layer_sample = h.isel({z_dim: slice(0, 5)}).mean().values
print(f"Layer thickness sample: {layer_sample}")

zw = np.cumsum(h, axis=h.dims.index(z_dim))
zc = zw - 0.5 * h  # midpoint of each layer

zc_sample_before = zc.isel({z_dim: slice(0, 5)}).mean().values
print(f"Before surface adjustment - zc sample: {zc_sample_before}")

# ensure positive-down, starting from surface = 0
zc = zc - zc.isel({z_dim: 0})

zc_sample_after = zc.isel({z_dim: slice(0, 5)}).mean().values
print(f"After surface adjustment - zc sample: {zc_sample_after}")
print(f"Source depth levels: {depth_src.size}, max={depth_src[-1]}")
print(f"Target local depths: shape {zc.shape}")
coord_setup_time = time.time() - coord_setup_start
print(f"⏱️  Coordinate setup took {coord_setup_time:.2f}s")

# ---------------------------------------------------------------------
# 4️⃣ Interpolate variable(s)
# ---------------------------------------------------------------------
outputs = {}

for variable_name in variables:
    # Extract source variable
    Tsrc = woa[variable_name]

    # 4a. Prepare output array
    array_setup_start = time.time()
    dims_out = zc.dims
    shape_out = zc.shape
    Tout = xr.zeros_like(zc)

    print("⚙️ Interpolating variable:", variable_name)

    # pick vertical, y, x dim names for target grid (zc)
    zdim = [d for d in zc.dims if d.lower().startswith("z")][0]
    ydim = [d for d in zc.dims if d.lower().startswith("y")][0]
    xdim = [d for d in zc.dims if d.lower().startswith("x")][0]

    # pick corresponding dim names for source data (Tsrc)
    Tsrc_ydim = None
    Tsrc_xdim = None
    for d in Tsrc.dims:
        if d.lower() in ['lat', 'latitude'] or d.lower().startswith("y"):
            Tsrc_ydim = d
        elif d.lower() in ['lon', 'longitude'] or d.lower().startswith("x"):
            Tsrc_xdim = d

    # Debug: check dimensions
    print(f"zc dimensions: {zc.dims}")
    print(f"Tsrc dimensions: {Tsrc.dims}")
    print(f"zc shape: {zc.shape}")
    print(f"Tsrc shape: {Tsrc.shape}")

    # Convert to numpy for easier indexing
    Tout_array = Tout.values
    zc_array = zc.values
    Tsrc_array = Tsrc.values

    # Get dimension order for proper indexing
    y_axis = Tout.dims.index(ydim)
    x_axis = Tout.dims.index(xdim)

    # Get dimension order for Tsrc using the detected dimension names
    Tsrc_y_axis = Tsrc.dims.index(Tsrc_ydim) if Tsrc_ydim else None
    Tsrc_x_axis = Tsrc.dims.index(Tsrc_xdim) if Tsrc_xdim else None
    print(f"Target y_axis: {y_axis}, x_axis: {x_axis}")
    print(f"Tsrc y_axis: {Tsrc_y_axis}, x_axis: {Tsrc_x_axis}")
    print(f"Tsrc ydim: {Tsrc_ydim}, xdim: {Tsrc_xdim}")

    # Find time dimension indices for both arrays
    time_axis = None
    for dim_idx, dim_name in enumerate(Tout.dims):
        if dim_name.lower().startswith('time'):
            time_axis = dim_idx
            break

    Tsrc_time_axis = None
    for dim_idx, dim_name in enumerate(Tsrc.dims):
        if dim_name.lower().startswith('time'):
            Tsrc_time_axis = dim_idx
            break

    # Prepare arguments for parallel processing
    idx_params = (
        y_axis, x_axis, time_axis, Tsrc_y_axis, Tsrc_x_axis,
        Tsrc_time_axis, Tout.shape
    )

    # Create latitude strips for parallel processing
    ny, nx = zc.sizes[ydim], zc.sizes[xdim]
    strip_size = max(1, ny // num_jobs)

    # Create job arguments with data strips to minimize memory transfer
    job_args = []
    for strip_start in range(0, ny, strip_size):
        strip_end = min(strip_start + strip_size, ny)

        # Extract strips of data for this chunk
        zc_strip = zc_array[:, :, strip_start:strip_end, :]
        Tsrc_strip = Tsrc_array[:, :, strip_start:strip_end, :]

        job_args.append(
            (strip_start, strip_end, zc_strip, Tsrc_strip, depth_src)
        )

    array_setup_time = time.time() - array_setup_start
    print(f"⏱️  Array setup took {array_setup_time:.2f}s")
    print(
        f"⏱️  Created {len(job_args)} strips for {num_jobs} processes"
    )

    # Run parallel interpolation
    print(f"🔄 Running interpolation with {num_jobs} processes...")
    interp_start = time.time()
    if num_jobs == 1:
        # Sequential processing
        all_results = []
        for args_tuple in tqdm(job_args, desc="Processing strips"):
            result = interpolate_latitude_strip(args_tuple)
            all_results.append(result)
    else:
        # Parallel processing
        with Pool(num_jobs) as pool:
            all_results = list(tqdm(
                pool.imap(interpolate_latitude_strip, job_args),
                total=len(job_args),
                desc="Processing strips"
            ))
    interp_time = time.time() - interp_start
    print(f"⏱️  Interpolation took {interp_time:.2f}s")

    # Combine results back into output array
    print("📦 Combining results...")
    assembly_start = time.time()
    for j_start, j_end, result_strip in all_results:
        # Copy the result strip back to the main array
        Tout_array[:, :, j_start:j_end, :] = result_strip
    assembly_time = time.time() - assembly_start
    print(f"⏱️  Result assembly took {assembly_time:.2f}s")

    # Name, attrs and store for output
    Tout = Tout.assign_coords({zdim: np.arange(Tout.sizes[zdim])})
    out_name = mapped_name(variable_name, outputs)
    if out_name != variable_name:
        print(f"   Renaming {variable_name} -> {out_name}")
    Tout.name = out_name

    # Copy original attributes and update
    if variable_name in woa:
        Tout.attrs.update(woa[variable_name].attrs)

    # Add interpolation info
    long_name_base = Tout.attrs.get('long_name', variable_name)
    long_name = f"{long_name_base} interpolated onto MOM6 layer centers"
    Tout.attrs.update({
        "long_name": long_name,
        "interpolation_method": "linear vertical interpolation",
        "original_source": woa_file,
    })

    outputs[out_name] = Tout

# ---------------------------------------------------------------------
# 5️⃣ Write output
# ---------------------------------------------------------------------
write_start = time.time()
appended = False

if os.path.exists(out_file):
    print(f"📎 Existing file detected, appending variables → {out_file}")
    try:
        ds = xr.open_dataset(out_file, decode_times=False)
        ds.load()  # bring into memory so we can safely close file handle
        ds.close()
    except Exception as e:
        sys.exit(f"❌ Failed to open existing output file for append: {e}")

    # Merge/overwrite variables
    for vname, da in outputs.items():
        if vname in ds:
            print(f"   Overwriting variable: {vname}")
        else:
            print(f"   Adding variable: {vname}")
        ds[vname] = da

    # Rewrite file with merged content
    ds.to_netcdf(out_file, format="NETCDF4_CLASSIC")
    appended = True
    var_names = list(ds.data_vars)
else:
    ds_out = xr.Dataset(outputs)
    ds_out.to_netcdf(out_file, format="NETCDF4_CLASSIC")
    var_names = list(outputs.keys())

write_time = time.time() - write_start
total_time = time.time() - start_time

print(f"⏱️  File writing took {write_time:.2f}s")
if appended:
    print(f"✅ Appended variables to file → {out_file}")
else:
    print(f"✅ Wrote vertically remapped file → {out_file}")
print(f"   Variables: {', '.join(var_names)}")
# Print shape/levels of the first variable for reference
first_var = next(iter(outputs))
print(f"   Sample variable: {first_var}")
print(f"   Shape: {outputs[first_var].shape}")
zdim_out = [d for d in outputs[first_var].dims if d.lower().startswith('z')][0]
print(f"   Vertical levels: {outputs[first_var].sizes[zdim_out]}")
print("")
print("⏱️  === VERTICAL INTERPOLATION TIMING ===")
print(f"Data loading:       {ldata:.2f}s")
print(f"Coordinate setup:   {coord_setup_time:.2f}s")
print(f"File writing:       {write_time:.2f}s")
print(f"Total time:         {total_time:.2f}s")
print("Parallel efficiency: N/A (per-variable timing shown above)")
