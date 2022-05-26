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
        'start': '2021-12-25T00:00:00Z',
        'end': '2021-12-27T00:00:00Z',
        'step': 'PT6H',
        'forecast_steps': ['PT6H'],
        'file_type_list': ['fv_core.res', 'fv_srf_wnd.res', 'fv_tracer.res', 'phy_data', 'sfc_data'],
        'source_dir': '/work2/noaa/da/rtreadon/data/',
        'source_file_fmt': '{source_dir}/enkf{dump}.{year}{month}{day}/{hour}/atmos/\
mem001/RESTART/$(valid_date).$(file_type).tile$(tile).nc',
        'type': 'fc',
        'model': 'gfs',
        'resolution': 'c384',
        'database': 'shared',
        'dump': 'gdas',
        'experiment': 'oper_gdas',
        'tile': [1, 2, 3, 4, 5, 6],
        'user_date_format': '%Y%m%d.%H%M%S',
        'fc_date_rendering': 'analysis',
    }
    yamlfile = os.path.join(os.getcwd(), 'store_gfs_bkg.yaml')
    with open(yamlfile, 'w') as f:
        yaml.dump(config, f, sort_keys=False, default_flow_style=False)
    store_bkg(yamlfile)
    # replace gfs with gfs_metadata
    config['model'] = 'gfs_metadata'
    config['source_file_fmt'] = '{source_dir}/enkf{dump}.{year}{month}{day}/{hour}/atmos/\
mem001/RESTART/$(valid_date).$(file_type)'
    config['file_type_list'] = ['coupler.res', 'fv_core.res.nc']
    del config['tile']
    yamlfile = os.path.join(os.getcwd(), 'store_gfs_coupler.yaml')
    with open(yamlfile, 'w') as f:
        yaml.dump(config, f, sort_keys=False, default_flow_style=False)
    store_bkg(yamlfile)
