#!/usr/bin/env python3

import sys
import os
import shutil
import subprocess
from pathlib import Path
import generate_soca_resources as gensoca

def main(project_src_dir):
    gdas_test_dir = Path.cwd()

    ## fv3-jedi resources
    print(f"src directory: {project_src_dir}")
    fmsmpp_nml = os.path.join(project_src_dir, "..", "sorc", "fv3-jedi", "test", "Data", "fv3files", "fmsmpp.nml")
    field_table = os.path.join(project_src_dir, "..", "sorc", "fv3-jedi", "test", "Data", "fv3files", "field_table_ufs")

    for tile in range(1, 7):
        subprocess.run(["ncgen", "-4", "-o", f"oro_data.tile{tile}.nc",
                        f"{project_src_dir}/soca/test/testdata/fv3jedi/C12_oro_data.tile{tile}.cdl"],
                       check=True)
        subprocess.run(["ncgen", "-4", "-o", f"sfc_data.tile{tile}.nc",
                        f"{project_src_dir}/soca/test/testdata/fv3jedi/20201214.210000.sfc_data.tile{tile}.cdl"],
                       check=True)


    # Create the directory for the fv3-jedi data
    data_dir = os.path.join(gdas_test_dir, "fv3-jedi")

    # Copy the resource files to the data directory
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    shutil.copy(fmsmpp_nml, data_dir)
    shutil.copy(field_table, data_dir)

    ## soca resources
    data_dir = os.path.join(gdas_test_dir, "soca")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    gensoca.generate_mom6_input("mom6_input.nml")
    gensoca.generate_MOM_input("MOM_input")
    subprocess.run(["ncgen", "-4", "-o", "soca/soca_gridspec.nc", f"{project_src_dir}/soca/test/testdata/soca_gridspec.cdl"], check=True)
    subprocess.run(["ncgen", "-4", "-o", "ocn.nc", f"{project_src_dir}/soca/test/testdata/ocn.cdl"], check=True)
    subprocess.run(["ncgen", "-4", "-o", "ice.nc", f"{project_src_dir}/soca/test/testdata/ice.cdl"], check=True)
    yaml_src_path = f"{project_src_dir}/../parm/marine/fields_metadata.yaml"
    shutil.copy(yaml_src_path, os.path.join(gdas_test_dir, "soca"))

if __name__ == "__main__":
    main(sys.argv[1])
