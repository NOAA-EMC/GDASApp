import os
from solo.configuration import Configuration
import ufsda.r2d2
import yaml


def store_bkg(yamlfile):
    config = Configuration(yamlfile)
    ufsda.r2d2.store(config)


if __name__ == "__main__":
    # first create dict of config for UFS RESTART files
    config = {
        'start': '2021-12-21T00:00:00Z',
        'end': '2021-12-21T18:00:00Z',
        'step': 'PT6H',
        'forecast_steps': ['PT6H'],
        'source_dir': '/work/noaa/stmp/rtreadon/comrot/prufsda/',
        'source_file_fmt': '{source_dir}/{dump}.{year}{month}{day}/{hour}/atmos/\
RESTART_GES/$(valid_date).$(file_type).tile$(tile).nc',
        'type': 'fc',
        'model': 'gfs',
        'resolution': 'c96',
        'database': 'shared',
        'dump': 'gdas',
        'experiment': 'oper_gdas',
    }
    yamlfile = os.path.join(os.getcwd(), 'store_gfs_bkg.yaml')
    with open(yamlfile, 'w') as f:
        yaml.dump(config, f, sort_keys=False, default_flow_style=False)
    store_bkg(yamlfile)
    # replace gfs with gfs_metadata
    config['model'] = 'gfs_metadata'
    config['source_file_fmt'] = '{source_dir}/{dump}.{year}{month}{day}/{hour}/atmos/\
RESTART_GES/$(valid_date).coupler.res'
    yamlfile = os.path.join(os.getcwd(), 'store_gfs_coupler.yaml')
    with open(yamlfile, 'w') as f:
        yaml.dump(config, f, sort_keys=False, default_flow_style=False)
    store_bkg(yamlfile)
