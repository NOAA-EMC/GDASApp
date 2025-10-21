# WOA → MOM6 interpolation utilities

Small utilities to build MOM6-ready climatologies from World Ocean Atlas (WOA) data using NOAA/FRE tools, perform vertical interpolation to MOM6 layers, and optionally time‑interpolate between monthly products.

## Components
- `woa_to_mom6.py` — Orchestrates horizontal remapping with FRE (`make_hgrid`, `make_solo_mosaic`, `fregrid`).
  - Config‑driven: accepts a Python dict or a YAML/JSON config file.
  - Supports WOA23 downloading (annual or monthly), multiple variables, and explicit remap weights file.
- `vert_interp_3d.py` — Vertically interpolates variables from pressure/depth levels onto MOM6 layer centers.
  - Renames outputs: `t_* → Temp`, `s_* → Salt` (collision‑safe).
- `gen_clim.py` — Minimal driver showing how to build annual/monthly climatologies by calling `woa_to_mom6.main(CONFIG)`.
- `splice_clim.py` — Mid‑month‑anchored time interpolation between monthly layer files for a single variable (default `Temp`).

## Dependencies
- FRE tools in PATH: `make_hgrid`, `make_solo_mosaic`, `fregrid`.
- Python 3 with: `xarray`, `netCDF4`, `numpy`, and optionally `PyYAML` (for YAML configs).
- A target MOM6 mosaic (`ocean_mosaic.nc`) and, for vertical interpolation, a MOM6 layer file (e.g., `MOM6_layer_h.nc`).

### Installing FRE utilities
You must have the FRE utilities available before running these tools.

- On HPC systems (Hera, Orion, WCOSS2, etc.), prefer loading site modules that provide the FRE tools.
- From source: clone and build the NOAA/GFDL FRE NCtools which contain `fregrid`, `make_hgrid`, and `make_solo_mosaic`.
  - Repository: https://github.com/NOAA-GFDL/FRE-NCtools
  - Requirements: C/Fortran compiler, MPI, HDF5, NetCDF-C, NetCDF-Fortran
  - Build and install, then ensure the install `bin/` is on your `PATH` so the commands are discoverable.

Load the GDASApp modules if building on HPC.
```bash
git clone https://github.com/NOAA-GFDL/FRE-NCtools
cd FRE-NCtools
autoreconf -i
mkdir build && cd build
../configure --prefix=<install path>
make
make install
```

## Quick start
1) Use the example driver:
- Edit `gen_clim.py` paths (e.g., `output_mosaic`, `layer_file`) and run it to generate an annual product (and monthly, if you un‑comment the loop).

2) Or run with a YAML config (example):
```yaml
# config.yml
download_woa23: true
woa23_var: temperature            # temperature | salinity
woa23_resolution: "0.25"          # 0.25 | 1.00 | 5.00
woa23_period: annual              # annual | monthly
# woa23_month: "01"              # when monthly
woa23_outdir: ./woa23

nlon: 2880
nlat: 1440
xbnds: [-180, 180]
ybnds: [-90, 90]

scalar_field: [t_an, t_sd]        # list, space, or comma‑separated
interp_method: conserve_order1
no_extrapolate: false

output_mosaic: /path/to/ocean_mosaic.nc
output_file: woa_on_mom6.nc

vertical: true
layer_file: /path/to/MOM6_layer_h.nc
vert_output: woa_on_mom6_layers.nc

# Set distinct weights for annual vs monthly runs if desired
remap_file: woa_to_mom6_weights_annual.nc
```
Then run:
```
python woa_to_mom6.py config.yml
```

3) Monthly climatologies:
- Set `woa23_period: monthly`, `woa23_month: "MM"`, and unique `output_file`/`vert_output`. You can share or separate `remap_file` for monthly vs annual.

## Time interpolation (splice)
Once monthly layer files (`woa_on_mom6_layers_MM.nc`) exist, create a time‑interpolated field at a target datetime:
```
./splice_clim.py YYYYMMDDHH [dir] [out.nc] [variable]
```
- Mid‑month anchoring between consecutive months.
- Interpolates only the requested variable (default `Temp`).

## Notes
- `scalar_field` is applied to horizontal remapping (all variables are passed to `fregrid`); the vertical step will try to process the same list.
- Bounds: `xbnds` and `ybnds` accept two numbers (e.g., `[-180, 180]`, `[-90, 90]`).
- If `remap_file` is omitted, a weights filename is derived from the input file name.
- Default interpolation method is `conserve_order1`; extrapolation is enabled unless `no_extrapolate: true`.
