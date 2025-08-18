#!/usr/bin/env python3
"""
Utility to generate a coupled scratch directory containing all resources
required to run both soca and fv3-jedi components.

This script creates a self-contained scratch directory with:
- fv3-jedi/ subdirectory with necessary FV3-JEDI resources
- soca/ subdirectory with necessary SOCA resources

The generated directories are ready for use in coupled experiments.
"""

import argparse
import sys
import os
import shutil
import subprocess
from pathlib import Path


def setup_fv3_jedi_resources(output_dir, atm_static_dir, atm_backgrounds, project_src_dir=None):
    """
    Set up FV3-JEDI resources in the scratch directory.
    
    Args:
        output_dir (Path): Output scratch directory
        atm_static_dir (str): Path to atmosphere static files
        atm_backgrounds (list): List of paths to atmosphere background files
        project_src_dir (str): Path to project source directory (for test data)
    """
    fv3_jedi_dir = output_dir / "fv3-jedi"
    fv3_jedi_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Setting up FV3-JEDI resources in {fv3_jedi_dir}")
    
    # Copy atmosphere static files if provided
    if atm_static_dir and os.path.exists(atm_static_dir):
        for file in os.listdir(atm_static_dir):
            src_file = os.path.join(atm_static_dir, file)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, fv3_jedi_dir)
                print(f"Copied {file} to fv3-jedi/")
    
    # Copy atmosphere background files
    for bg_file in atm_backgrounds:
        if os.path.exists(bg_file):
            shutil.copy2(bg_file, fv3_jedi_dir)
            print(f"Copied atmosphere background {os.path.basename(bg_file)} to fv3-jedi/")
    
    # If project source directory is provided, use test data
    if project_src_dir:
        # Look for FV3-JEDI static files in the project
        fmsmpp_nml = os.path.join(project_src_dir, "..", "sorc", "fv3-jedi", "test", "Data", "fv3files", "fmsmpp.nml")
        field_table = os.path.join(project_src_dir, "..", "sorc", "fv3-jedi", "test", "Data", "fv3files", "field_table_ufs")
        
        if os.path.exists(fmsmpp_nml):
            shutil.copy2(fmsmpp_nml, fv3_jedi_dir)
            print("Copied fmsmpp.nml to fv3-jedi/")
        
        if os.path.exists(field_table):
            shutil.copy2(field_table, fv3_jedi_dir)
            print("Copied field_table_ufs to fv3-jedi/")
        
        # Generate tile data files from test data
        try:
            for tile in range(1, 7):
                oro_cdl = f"{project_src_dir}/soca/test/testdata/fv3jedi/C12_oro_data.tile{tile}.cdl"
                sfc_cdl = f"{project_src_dir}/soca/test/testdata/fv3jedi/20201214.210000.sfc_data.tile{tile}.cdl"
                
                if os.path.exists(oro_cdl):
                    oro_nc = fv3_jedi_dir / f"oro_data.tile{tile}.nc"
                    subprocess.run(["ncgen", "-4", "-o", str(oro_nc), oro_cdl], check=True)
                    print(f"Generated oro_data.tile{tile}.nc")
                
                if os.path.exists(sfc_cdl):
                    sfc_nc = fv3_jedi_dir / f"sfc_data.tile{tile}.nc"
                    subprocess.run(["ncgen", "-4", "-o", str(sfc_nc), sfc_cdl], check=True)
                    print(f"Generated sfc_data.tile{tile}.nc")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Warning: Could not generate NetCDF files from test data: {e}")
            print("This may be due to missing ncgen tool. NetCDF files will be skipped.")


def setup_soca_resources(output_dir, ocean_static_dir, ocean_backgrounds, ice_backgrounds, project_src_dir=None):
    """
    Set up SOCA resources in the scratch directory.
    
    Args:
        output_dir (Path): Output scratch directory
        ocean_static_dir (str): Path to ocean static files  
        ocean_backgrounds (list): List of paths to ocean background files
        ice_backgrounds (list): List of paths to ice background files
        project_src_dir (str): Path to project source directory (for test data)
    """
    soca_dir = output_dir / "soca"
    soca_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Setting up SOCA resources in {soca_dir}")
    
    # Copy ocean static files if provided
    if ocean_static_dir and os.path.exists(ocean_static_dir):
        for file in os.listdir(ocean_static_dir):
            src_file = os.path.join(ocean_static_dir, file)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, soca_dir)
                print(f"Copied {file} to soca/")
    
    # Copy ocean background files
    for bg_file in ocean_backgrounds:
        if os.path.exists(bg_file):
            shutil.copy2(bg_file, soca_dir)
            print(f"Copied ocean background {os.path.basename(bg_file)} to soca/")
    
    # Copy ice background files
    for bg_file in ice_backgrounds:
        if os.path.exists(bg_file):
            shutil.copy2(bg_file, soca_dir)
            print(f"Copied ice background {os.path.basename(bg_file)} to soca/")
    
    # Generate MOM6 and MOM input files
    generate_mom6_input(soca_dir / "mom6_input.nml")
    generate_MOM_input(soca_dir / "MOM_input")
    
    # If project source directory is provided, use test data and generate additional resources
    if project_src_dir:
        # Copy fields metadata yaml
        yaml_src_path = f"{project_src_dir}/../parm/soca/fields_metadata.yaml"
        if os.path.exists(yaml_src_path):
            shutil.copy2(yaml_src_path, soca_dir)
            print("Copied fields_metadata.yaml to soca/")
        
        # Create INPUT subdirectory
        input_dir = soca_dir / "INPUT"
        input_dir.mkdir(exist_ok=True)
        
        # Generate NetCDF files from test CDL data
        try:
            cdl_files = [
                ("soca_gridspec.nc", f"{project_src_dir}/soca/test/testdata/soca_gridspec.cdl"),
                ("ocn.nc", f"{project_src_dir}/soca/test/testdata/ocn.cdl"), 
                ("ice.nc", f"{project_src_dir}/soca/test/testdata/ice.cdl"),
                ("INPUT/grid_spec.nc", f"{project_src_dir}/soca/test/testdata/grid_spec.cdl"),
                ("INPUT/ocean_mosaic.nc", f"{project_src_dir}/soca/test/testdata/ocean_mosaic.cdl")
            ]
            
            for nc_file, cdl_file in cdl_files:
                if os.path.exists(cdl_file):
                    output_nc = soca_dir / nc_file
                    ncgen_cmd = ["ncgen"]
                    # Use netCDF-3 for grid_spec.nc and ocean_mosaic.nc, netCDF-4 for others
                    if "INPUT/" in nc_file:
                        ncgen_cmd.extend(["-3"])
                    else:
                        ncgen_cmd.extend(["-4"])
                    ncgen_cmd.extend(["-o", str(output_nc), cdl_file])
                    
                    subprocess.run(ncgen_cmd, check=True)
                    print(f"Generated {nc_file}")
            
            # Try to import and use generate_soca_resources functionality if available
            try:
                sys.path.insert(0, os.path.join(project_src_dir, "soca", "test"))
                import generate_soca_resources as gensoca
                
                # Change to soca directory to run the generators
                original_cwd = os.getcwd()
                os.chdir(soca_dir)
                
                try:
                    # Generate increment file if we have ocean background
                    if os.path.exists(soca_dir / "ocn.nc"):
                        gensoca.genincr("ocn.nc", "ocn.incr.nc")
                        print("Generated ocean increment file")
                        
                        # Generate ensemble members
                        if os.path.exists(soca_dir / "ice.nc"):
                            gensoca.genperts('ocn.nc', 'ocn.incr.nc', 'ice.nc', 'ice.nc', './')
                            print("Generated ensemble perturbations")
                            
                finally:
                    os.chdir(original_cwd)
                    
            except ImportError as e:
                print(f"Warning: Could not import generate_soca_resources: {e}")
            except Exception as e:
                print(f"Warning: Could not generate additional SOCA resources: {e}")
                
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Warning: Could not generate NetCDF files from test data: {e}")
            print("This may be due to missing ncgen tool. NetCDF files will be skipped.")


def generate_mom6_input(output_file):
    """Generate MOM6 input namelist file."""
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
    with open(output_file, 'w') as f:
        f.write(content.strip() + '\n')
    print(f"Generated {output_file}")


def generate_MOM_input(output_file):
    """Generate MOM input parameter file."""
    content = """
NIGLOBAL = 36
NJGLOBAL = 17
NK = 5
TRIPOLAR_N=True
TOPO_CONFIG = "file"
"""
    with open(output_file, 'w') as f:
        f.write(content.strip() + '\n')
    print(f"Generated {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a coupled scratch directory for soca and fv3-jedi experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate scratch directory with test data
  %(prog)s --output-dir /path/to/scratch --use-test-data /path/to/GDASApp/utils

  # Generate with custom static files and backgrounds
  %(prog)s --output-dir /path/to/scratch \\
           --atm-static-dir /path/to/atm/static \\
           --ocean-static-dir /path/to/ocean/static \\
           --atm-backgrounds /path/to/atm/bg1.nc /path/to/atm/bg2.nc \\
           --ocean-backgrounds /path/to/ocean/bg.nc \\
           --ice-backgrounds /path/to/ice/bg.nc
        """
    )
    
    parser.add_argument("--output-dir", required=True,
                        help="Output directory for the coupled scratch directory")
    
    parser.add_argument("--atm-static-dir", 
                        help="Path to directory containing atmosphere static files")
    
    parser.add_argument("--ocean-static-dir",
                        help="Path to directory containing ocean static files")
                        
    parser.add_argument("--atm-backgrounds", nargs="*", default=[],
                        help="Paths to atmosphere background files")
                        
    parser.add_argument("--ocean-backgrounds", nargs="*", default=[],
                        help="Paths to ocean background files")
                        
    parser.add_argument("--ice-backgrounds", nargs="*", default=[],
                        help="Paths to sea ice background files")
    
    parser.add_argument("--use-test-data",
                        help="Path to project source directory to use test data (e.g., /path/to/GDASApp/utils)")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not any([args.atm_static_dir, args.ocean_static_dir, args.atm_backgrounds, 
                args.ocean_backgrounds, args.ice_backgrounds, args.use_test_data]):
        parser.error("At least one input source must be provided (static directories, backgrounds, or --use-test-data)")
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating coupled scratch directory in: {output_dir}")
    
    # Set up FV3-JEDI resources
    setup_fv3_jedi_resources(
        output_dir=output_dir,
        atm_static_dir=args.atm_static_dir,
        atm_backgrounds=args.atm_backgrounds,
        project_src_dir=args.use_test_data
    )
    
    # Set up SOCA resources  
    setup_soca_resources(
        output_dir=output_dir,
        ocean_static_dir=args.ocean_static_dir,
        ocean_backgrounds=args.ocean_backgrounds,
        ice_backgrounds=args.ice_backgrounds,
        project_src_dir=args.use_test_data
    )
    
    print(f"\nCoupled scratch directory created successfully at: {output_dir}")
    print(f"Directory structure:")
    print(f"  {output_dir}/")
    print(f"  ├── fv3-jedi/")
    print(f"  └── soca/")
    
    # Show directory contents
    for subdir in ["fv3-jedi", "soca"]:
        subdir_path = output_dir / subdir
        if subdir_path.exists():
            files = list(subdir_path.iterdir())
            print(f"      {subdir}/ contains {len(files)} files/directories")
            if args.verbose:
                for file in sorted(files):
                    print(f"        - {file.name}")


if __name__ == "__main__":
    main()