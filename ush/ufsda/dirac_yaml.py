#!/usr/bin/env python3
# convert a var yaml to a dirac yaml
import yaml
import xarray as xr
import numpy as np
from itertools import repeat
import argparse
import dateutil


def var2dirac(args):

    # Variables of convenience
    varyaml = args.varyaml
    diracyaml = args.diracyaml
    grid = args.fields
    dim1 = args.dim1
    dim2 = args.dim2
    ndiracs = args.ndiracs
    level = args.level
    field = args.fieldindex
    statevars = args.statevars
    output = args.diracoutput

    # Parse the variational yaml
    with open(varyaml, 'r') as file:
        varconfig = yaml.load(file, Loader=yaml.SafeLoader)

    # Exctract the necessary configuration from the var yaml
    diracconfig = {}
    diracconfig['geometry'] = varconfig['cost function']['geometry']
    diracconfig['initial condition'] = varconfig['cost function']['background']
    diracconfig['background error'] = varconfig['cost function']['background error']

    # Overwrite variables
    diracconfig['initial condition']['state variables'] = statevars
    diracconfig['background error']['linear variable change']['input variables'] = statevars
    diracconfig['background error']['linear variable change']['output variables'] = statevars

    # Generate impulse indices
    ds = xr.open_dataset(grid)
    ni = ds.dims[dim1]
    nj = ds.dims[dim2]
    step = ni*nj/ndiracs
    stepi = int(ni/(ni+nj)*step)
    stepj = int(nj/(ni+nj)*step)
    ixdir, iydir = np.meshgrid(np.arange(1, ni, stepi),
                               np.arange(1, nj, stepj))
    ixdir = ixdir.reshape(-1).tolist()
    iydir = iydir.reshape(-1).tolist()

    listsize = len(ixdir)
    izdir = list(repeat(level, listsize))
    ifdir = list(repeat(field, listsize))

    dirconfig = {}
    dirconfig['ixdir'] = ixdir
    dirconfig['iydir'] = iydir
    dirconfig['izdir'] = izdir
    dirconfig['ifdir'] = ifdir

    diracconfig['dirac'] = dirconfig

    # Read the model dependent incrememnt output configuration
    diracconfig['output dirac'] = yaml.safe_load(open(output, 'r'))

    # Fix the date
    dirac_date = dateutil.parser.parse(str(diracconfig['initial condition']['date']))
    diracconfig['initial condition']['date'] = dirac_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Write the dirac yaml
    with open(diracyaml, 'w') as f:
        yaml.dump(diracconfig, f, sort_keys=False, default_flow_style=False, Dumper=yaml.SafeDumper)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--varyaml', type=str, help='Variational YAML used in the cycle', required=True)
    parser.add_argument('--fields', type=str,
                        help='A file containing an incrememnt field (used to get the dimensions)', required=True)
    parser.add_argument('--dim1', type=str, help='Name of the longitude dimension', required=True)
    parser.add_argument('--dim2', type=str, help='Name of the latitude dimension', required=True)
    parser.add_argument('--diracyaml', type=str, help='Name of the output dirac YAML', required=True)
    parser.add_argument('--ndiracs', type=int, help='Number of impulses', required=True)
    parser.add_argument('--level', type=int, help='Model level of the impulse', required=True)
    parser.add_argument('--fieldindex', type=int,
                        help='Index of the field for which to generate the impulse', required=True)
    parser.add_argument('--statevars', type=str,
                        help='List of variables to read from the trajectory', nargs='+', required=True)
    parser.add_argument('--diracoutput', type=str,
                        help='A yaml file containing the dictionary that the model uses to write an incremement',
                        required=True)
    args = parser.parse_args()

    var2dirac(args)
