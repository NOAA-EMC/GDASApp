#!/usr/bin/env python3
import os
import shlex
import subprocess
import sys
import time
import json
from urllib.request import urlopen

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def run(cmd, env=None):
    if isinstance(cmd, str):
        printable = cmd
        shell = True
    else:
        printable = " ".join(shlex.quote(c) for c in cmd)
        shell = False
    start = time.time()
    print(f"$ {printable}")
    try:
        res = subprocess.run(cmd, shell=shell, env=env, check=True)
        rc = res.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        raise
    dur = int(time.time() - start)
    return rc, dur


# Replace CLI parsing with config-based loading
# ------------------------------------------------
DEFAULTS = {
    "input_file": "woa18_decav_t00_01.nc",
    "output_file": "WOA18_on_MOM6.nc",
    "dlon": 0.5,
    "dlat": 0.5,
    "xbnds": [-180.0, 180.0],
    "ybnds": [-90.0, 90.0],
    "grid_name": "woa_grid",
    "mosaic_name": "woa_mosaic",
    "output_mosaic": "./dst/ocean_mosaic.nc",
    # Remapping weights file (set empty to auto-name from input file)
    "remap_file": "",
    "scalar_field": "t_an",
    "interp_method": "conserve_order1",
    "no_extrapolate": False,
    # Vertical
    "vertical": False,
    "layer_file": "./dst/MOM6_layer_h.nc",
    "vert_output": "WOA18_on_MOM6_layers.nc",
    "depth_var": "depth",
    "layer_var": "h",
    "jobs": None,
    # WOA23 download
    "download_woa23": False,
    "woa23_var": "temperature",  # temperature | salinity
    "woa23_resolution": "0.25",  # 0.25 | 1.00 | 5.00
    "woa23_period": "annual",    # annual | monthly
    "woa23_month": "",
    "woa23_outdir": "./woa23",
}


def _deepcopy_defaults():
    # avoid sharing list objects like xbnds/ybnds
    d = dict(DEFAULTS)
    d["xbnds"] = list(DEFAULTS["xbnds"])  # type: ignore
    d["ybnds"] = list(DEFAULTS["ybnds"])  # type: ignore
    return d


def _normalize_bounds(val, name):
    # Accept [min, max], (min, max), "min,max", or "min max"
    if isinstance(val, (list, tuple)) and len(val) == 2:
        return [float(val[0]), float(val[1])]
    if isinstance(val, str):
        sep = "," if "," in val else " "
        parts = [p for p in val.split(sep) if p]
        if len(parts) == 2:
            return [float(parts[0]), float(parts[1])]
    print(f"❌ Invalid {name}: {val} (expect two numbers)")
    sys.exit(2)


def load_config(config):
    # config can be a dict or a path to YAML/JSON
    cfg = _deepcopy_defaults()
    if config is None:
        print("Usage: woa_to_mom6.py <config.(yml|yaml|json)>")
        sys.exit(2)

    if isinstance(config, dict):
        user = config
    else:
        path = str(config)
        if not os.path.isfile(path):
            print(f"❌ Config file not found: {path}")
            sys.exit(2)
        try:
            if path.endswith(('.yml', '.yaml')):
                if yaml is None:
                    print("❌ PyYAML is required for YAML configs")
                    sys.exit(2)
                with open(path, 'r') as f:
                    user = yaml.safe_load(f) or {}
            else:
                with open(path, 'r') as f:
                    user = json.load(f)
        except Exception as e:
            print(f"❌ Failed to read config {path}: {e}")
            sys.exit(2)

    # Merge
    for k, v in (user or {}).items():
        cfg[k] = v

    # Normalize
    cfg["xbnds"] = _normalize_bounds(cfg.get("xbnds"), "xbnds")
    cfg["ybnds"] = _normalize_bounds(cfg.get("ybnds"), "ybnds")

    return cfg


def ensure_file(path):
    if not os.path.isfile(path):
        print(f"Error: Required file not found: {path}")
        sys.exit(1)


def split_fields(field_arg):
    # Accept string or list(s) of strings; split on comma/space and
    # deduplicate preserving order. Default to ["t_an"] if None.
    def add_tokens(val, acc):
        for chunk in str(val).replace(",", " ").split():
            if chunk and chunk not in acc:
                acc.append(chunk)

    if field_arg is None:
        return ["t_an"]

    tokens = []
    if isinstance(field_arg, (list, tuple)):
        for item in field_arg:
            if isinstance(item, (list, tuple)):
                for sub in item:
                    add_tokens(sub, tokens)
            else:
                add_tokens(item, tokens)
    else:
        add_tokens(field_arg, tokens)
    return tokens


def map_resolution(res):
    if res in ("0.25", "0.250"):
        return "0.25", "04"
    if res in ("1.00", "1", "1.0"):
        return "1.00", "01"
    if res in ("5.00", "5", "5.0"):
        return "5.00", "5d"
    print(f"❌ Invalid --woa23-resolution: {res} (use 0.25 | 1.00 | 5.00)")
    sys.exit(1)


def build_woa23_base(var_family):
    # var_family: 'temperature' or 'salinity'
    return (
        "https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/"
        f"{var_family}/netcdf/decav"
    )


def var_code(var_family):
    # filename variable code: t or s
    return "t" if var_family == "temperature" else "s"


def download_woa23(var_family, resolution, period, month, outdir):
    base = build_woa23_base(var_family)
    code_char = var_code(var_family)
    res_dir, res_code = map_resolution(resolution)
    if period == "annual":
        fname = f"woa23_decav_{code_char}00_{res_code}.nc"
    else:
        mm = month or "01"
        if not (len(mm) == 2 and mm.isdigit() and 1 <= int(mm) <= 12):
            print(f"❌ Invalid --woa23-month: {mm} (use 01..12)")
            sys.exit(1)
        fname = f"woa23_decav_{code_char}{mm}_{res_code}.nc"
    url = f"{base}/{res_dir}/{fname}"

    os.makedirs(outdir, exist_ok=True)
    target = os.path.join(outdir, fname)
    if os.path.isfile(target):
        print(f"ℹ️  Using existing file: {target}")
        return target

    print(f"⬇️  Downloading {url}")
    try:
        with urlopen(url) as r, open(target, "wb") as f:
            f.write(r.read())
    except Exception as e:
        print(f"❌ Download failed: {e}")
        sys.exit(1)
    print(f"✅ WOA23 file ready: {target}")
    return target


def resolve_remap_file(cfg):
    # If provided, use it. Else derive from input filename
    # so weights are specific to the input (annual vs monthly)
    rf = cfg.get("remap_file")
    if rf:
        return rf
    base = os.path.basename(cfg.get("input_file"))
    stem, _ = os.path.splitext(base)
    return f"{stem}_weights.nc"


# Main pipeline driven by a config dict
# ------------------------------------------------

def main(config=None):
    # Support: main(dict) when imported, or script usage with a path argument
    if config is None:
        config = sys.argv[1] if len(sys.argv) > 1 else None
    cfg = load_config(config)

    # Optional download of WOA23 file
    if cfg.get("download_woa23"):
        cfg["input_file"] = download_woa23(
            cfg.get("woa23_var"),
            cfg.get("woa23_resolution"),
            cfg.get("woa23_period"),
            cfg.get("woa23_month"),
            cfg.get("woa23_outdir"),
        )

    # Validate inputs
    ensure_file(cfg.get("input_file"))
    if cfg.get("vertical"):
        ensure_file(cfg.get("layer_file"))
        script_dir = os.path.dirname(os.path.abspath(__file__))
        vert_script = os.path.join(script_dir, "vert_interp_3d.py")
        ensure_file(vert_script)

    # Fields
    fields = split_fields(cfg.get("scalar_field"))

    xb = cfg.get("xbnds")
    yb = cfg.get("ybnds")

    dx = cfg.get("dlon")
    dy = cfg.get("dlat")

    dlon_str = f"{dx},{dx}"
    dlat_str = f"{dy},{dy}"

    # Show configuration
    print("🌊 WOA to MOM6 Grid Interpolation (Python)")
    print("=========================================")
    t0 = time.time()
    print(f"Input file:       {cfg.get('input_file')}")
    print(f"Output file:      {cfg.get('output_file')}")
    print(f"Grid spacing:     {cfg.get('dlon')}×{cfg.get('dlat')}")
    print(f"Longitude bounds: {xb[0]} {xb[1]}")
    print(f"Latitude bounds:  {yb[0]} {yb[1]}")
    print(f"Grid name:        {cfg.get('grid_name')}")
    print(f"Mosaic name:      {cfg.get('mosaic_name')}")
    print(f"Scalar field(s):  {', '.join(fields)}")
    print(f"Interp method:    {cfg.get('interp_method')}")
    remap_file = resolve_remap_file(cfg)
    print(f"Remap weights:    {remap_file}")
    if cfg.get("vertical"):
        print("Vertical interp:  YES")
        print(f"Layer file:       {cfg.get('layer_file')}")
        print(f"Vert output:      {cfg.get('vert_output')}")
        print(f"Depth variable:   {cfg.get('depth_var')}")
        print(f"Layer variable:   {cfg.get('layer_var')}")
    else:
        print("Vertical interp:  NO")
    print("")

    # Create WOA input mosaic (regular lon/lat grid)
    print("🗂️  Creating grid...")
    rc, grid_sec = run([
        "make_hgrid",
        "--grid_type", "regular_lonlat_grid",
        "--dlon", dlon_str,
        "--dlat", dlat_str,
        "--nxbnds", "2",
        "--nybnds", "2",
        "--xbnds", f"{xb[0]},{xb[1]}",
        "--ybnds", f"{yb[0]},{yb[1]}",
        "--grid_name", cfg.get("grid_name"),
        "--center", "t_cell",
    ])
    print(f"⏱️  Grid creation took {grid_sec}s")

    print("🗂️  Creating mosaic...")
    rc, mosaic_sec = run([
        "make_solo_mosaic",
        "--num_tiles", "1",
        "--dir", ".",
        "--tile_file", f"{cfg.get('grid_name')}.nc",
        "--mosaic_name", cfg.get("mosaic_name"),
        "--periodx", "360",
    ])
    print(f"⏱️  Mosaic creation took {mosaic_sec}s")

    # fregrid call
    print("🔄 Interpolating data (horizontal)...")
    fregrid_cmd = [
        "fregrid",
        f"--input_file={cfg.get('input_file')}",
        f"--input_mosaic={cfg.get('mosaic_name')}.nc",
        f"--remap_file={remap_file}",
        f"--output_mosaic={cfg.get('output_mosaic')}",
        f"--output_file={cfg.get('output_file')}",
        f"--interp_method={cfg.get('interp_method')}",
        f"--scalar_field={','.join(fields)}",
    ]
    if not cfg.get("no_extrapolate"):
        fregrid_cmd.append("--extrapolate")
    try:
        _, horiz_sec = run(" ".join(fregrid_cmd))
    except subprocess.CalledProcessError:
        sys.exit(1)
    print(f"⏱️  Horizontal interpolation took {horiz_sec}s")
    print(
        "✅ Horizontal interpolation complete! "
        f"Output: {cfg.get('output_file')}"
    )

    # Vertical interpolation
    if cfg.get("vertical"):
        print("")
        print("🔄 Performing vertical interpolation...")
        if not os.path.isfile(cfg.get("output_file")):
            print("❌ Error: Horizontal interpolation output not found!")
            sys.exit(1)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        vert_script = os.path.join(script_dir, "vert_interp_3d.py")

        cmd = [
            vert_script,
            "--woa-file", cfg.get("output_file"),
            "--layer-file", cfg.get("layer_file"),
            "--output-file", cfg.get("vert_output"),
            "--depth-var", cfg.get("depth_var"),
            "--layer-var", cfg.get("layer_var"),
        ]
        for v in fields:
            cmd.extend(["--variable", v])
        jobs = cfg.get("jobs")
        if jobs:
            cmd.extend(["--jobs", str(jobs)])

        try:
            _, vert_sec = run(cmd)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)

        print(f"⏱️  Vertical interpolation took {vert_sec}s")
        print(
            "✅ Vertical interpolation complete! "
            f"Output: {cfg.get('vert_output')}"
        )
        print("📋 Summary:")
        print(f"   Horizontal:  {cfg.get('output_file')}")
        print(f"   Vertical:    {cfg.get('vert_output')}")
    else:
        print("📋 Summary:")
        print(f"   Horizontal only:  {cfg.get('output_file')}")

    total_sec = int(time.time() - t0)
    print("")
    print("⏱️  === TIMING SUMMARY ===")
    print(f"Grid creation:      {grid_sec}s")
    print(f"Mosaic creation:    {mosaic_sec}s")
    print(f"Horizontal interp:  {horiz_sec}s")
    if cfg.get("vertical"):
        print(f"Vertical interp:    {vert_sec}s")
    print(f"Total runtime:      {total_sec}s")


if __name__ == "__main__":
    try:
        # Provide a path to a YAML/JSON config as the first argument,
        # or pass a dict when importing this module and calling main(dict).
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(130)
