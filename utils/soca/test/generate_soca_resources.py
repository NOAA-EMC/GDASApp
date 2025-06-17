#!/usr/bin/env python3

from netCDF4 import Dataset
import numpy as np
import sys
import os
import shutil
import subprocess
from pathlib import Path

def get_fill_value(var):
    """Returns the fill value for the variable, if defined."""
    for key in ["_FillValue", "missing_value"]:
        if key in var.ncattrs():
            return var.getncattr(k)
    return None

def compute_masked_anomaly(var, lat_dim, lon_dim):
    """
    Compute anomaly by removing masked horizontal mean over specified lat/lon dims.
    """
    data = var[:]
    fill_value = get_fill_value(var)

    # Mask out fill values
    if fill_value is not None:
        data = np.ma.masked_where(data == fill_value, data)
    else:
        data = np.ma.masked_invalid(data)

    # Axis indices
    axes = var.dimensions
    lat_axis = axes.index(lat_dim)
    lon_axis = axes.index(lon_dim)

    # Compute masked horizontal mean
    mean = data.mean(axis=(lat_axis, lon_axis), keepdims=True)
    anomaly = data - mean
    return anomaly.filled(fill_value), fill_value

def genincr(input_file, output_file):
    ds_in = Dataset(input_file, "r")
    ds_out = Dataset(output_file, "w")

    # Copy dimensions
    for name, dim in ds_in.dimensions.items():
        ds_out.createDimension(name, len(dim) if not dim.isunlimited() else None)

    # Copy coordinate variables
    for name in ds_in.variables:
        if name in ["Layer", "Time", "lath", "latq", "lonh", "lonq"]:
            var_in = ds_in.variables[name]
            var_out = ds_out.createVariable(name, var_in.datatype, var_in.dimensions)
            var_out.setncatts({k: var_in.getncattr(k) for k in var_in.ncattrs()})
            var_out[:] = var_in[:]

    # 4D variables with Layer
    var_info_4d = {
        "Temp": ("lath", "lonh"),
        "Salt": ("lath", "lonh"),
        "u":    ("lath", "lonq"),
        "v":    ("latq", "lonh")
    }

    for varname, (lat_dim, lon_dim) in var_info_4d.items():
        if varname not in ds_in.variables:
            continue
        var_in = ds_in.variables[varname]
        anomaly_data, fill_value = compute_masked_anomaly(var_in, lat_dim, lon_dim)

        var_anom_name = varname
        var_out = ds_out.createVariable(var_anom_name, var_in.datatype, var_in.dimensions,
                                        fill_value=fill_value)
        var_out.setncatts({k: var_in.getncattr(k) for k in var_in.ncattrs()})
        var_out.setncattr("long_name", f"{var_out.getncattr('long_name')} Anomaly")
        var_out[:] = 0.1 * anomaly_data

    # Add ave_ssh anomaly (3D: Time, lath, lonh)
    if "ave_ssh" in ds_in.variables:
        var = ds_in.variables["ave_ssh"]
        anomaly_data, fill_value = compute_masked_anomaly(var, "lath", "lonh")

        var_out = ds_out.createVariable("ave_ssh", var.datatype, var.dimensions,
                                        fill_value=fill_value)
        var_out.setncatts({k: var.getncattr(k) for k in var.ncattrs()})
        var_out.setncattr("long_name", f"{var.getncattr('long_name')} Anomaly")
        var_out[:] = 0.1 * anomaly_data

    ds_in.close()
    ds_out.close()
    print(f"Anomaly file with masking and ave_ssh anomaly written to {output_file}")


def genperts(ocean_bg, ocean_incr, ice_bg, ice_incr, output_dir):
    """
    Generate 2 ensemble members for ocean and ice by creating linear
    combinations of the background and increment inputs.

    Parameters:
        ocean_bg (str): Path to the ocean background file.
        ocean_incr (str): Path to the ocean increment file.
        ice_bg (str): Path to the ice background file.
        ice_incr (str): Path to the ice increment file.
        output_dir (str): Directory to save the generated ensemble members.
    """
    os.makedirs(output_dir, exist_ok=True)

    def create_ensemble_member(bg_file, incr_file, output_file, factor):
        with Dataset(bg_file, "r") as bg, Dataset(incr_file, "r") as incr, Dataset(output_file, "w") as out:
            # Copy dimensions
            for name, dim in bg.dimensions.items():
                out.createDimension(name, len(dim) if not dim.isunlimited() else None)

            # Copy variables and apply linear combination
            for name, var in bg.variables.items():
                var_out = out.createVariable(name, var.datatype, var.dimensions)
                var_out.setncatts({k: var.getncattr(k) for k in var.ncattrs()})
                if name in incr.variables:
                    var_out[:] = var[:] + factor * incr.variables[name][:]
                else:
                    var_out[:] = var[:]

    # Generate ensemble members for ocean
    create_ensemble_member(ocean_bg, ocean_incr, os.path.join(output_dir, "ocn.1.nc"), factor=0.5)
    create_ensemble_member(ocean_bg, ocean_incr, os.path.join(output_dir, "ocn.2.nc"), factor=-0.5)

    # Generate ensemble members for ice
    create_ensemble_member(ice_bg, ice_incr, os.path.join(output_dir, "ice.1.nc"), factor=0.5)
    create_ensemble_member(ice_bg, ice_incr, os.path.join(output_dir, "ice.2.nc"), factor=-0.5)

    print(f"Ensemble members generated in {output_dir}")

def generate_mom6_input(nml_path):
    content = """
 &MOM_input_nml
    output_directory = './',
    input_filename = 'r'
    restart_input_dir = 'INPUT/',
    parameter_filename = 'MOM_input' /

 &diag_manager_nml
 /

 &fms_io_nml
    max_files_w=100
    checksum_required=.false.
/

 &fms_nml
    clock_grain='MODULE'
    domains_stack_size = 2000000
    clock_flags='SYNC' /
"""
    with open(nml_path, 'w') as f:
        f.write(content.strip() + '\n')

def generate_MOM_input(file_path):
    content = """
NIGLOBAL = 36
NJGLOBAL = 17
NK = 5
TRIPOLAR_N=True
TOPO_CONFIG = "file"
"""
    with open(file_path, 'w') as f:
        f.write(content.strip() + '\n')

def main(project_src_dir):
    gdas_test_dir = Path.cwd()

    # Clean and recreate test workdir
#    if gdas_test_dir.exists():
#        shutil.rmtree(gdas_test_dir)
#    gdas_test_dir.mkdir(parents=True)
#
#    os.chdir(gdas_test_dir)
    print(f"src directory: {project_src_dir}")

    # Generate config files
    generate_mom6_input("mom6_input.nml")
    generate_MOM_input("MOM_input")

    # Convert CDL files to NetCDF
    subprocess.run(["ncgen", "-4", "-o", "soca_gridspec.nc", f"{project_src_dir}/soca/test/testdata/soca_gridspec.cdl"], check=True)
    subprocess.run(["ncgen", "-4", "-o", "ocn.nc", f"{project_src_dir}/soca/test/testdata/ocn.cdl"], check=True)
    subprocess.run(["ncgen", "-4", "-o", "ice.nc", f"{project_src_dir}/soca/test/testdata/ice.cdl"], check=True)

    # INPUT dir with NetCDF files
    input_dir = gdas_test_dir / "INPUT"
    input_dir.mkdir(exist_ok=True)

    subprocess.run(["ncgen", "-3", "-o", input_dir / "grid_spec.nc", f"{project_src_dir}/soca/test/testdata/grid_spec.cdl"], check=True)
    subprocess.run(["ncgen", "-3", "-o", input_dir / "ocean_mosaic.nc", f"{project_src_dir}/soca/test/testdata/ocean_mosaic.cdl"], check=True)

    # Copy YAML file
    yaml_src_path = f"{project_src_dir}/../parm/soca/fields_metadata.yaml"
    shutil.copy(yaml_src_path, gdas_test_dir)

    # Generate increment file
    genincr("ocn.nc", "ocn.incr.nc")

    # Generate ensemble members
    genperts('ocn.nc', 'ocn.incr.nc', 'ice.nc', 'ice.nc', './')

if __name__ == "__main__":
    main(sys.argv[1])
