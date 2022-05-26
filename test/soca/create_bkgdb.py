#!/usr/bin/env python3
import os
import shutil
from solo.configuration import Configuration
from solo.nice_dict import NiceDict
import ufsda.r2d2
from dateutil import parser
import datetime

if __name__ == "__main__":

    # Setup the shared R2D2 databases
    ufsda.r2d2.setup(r2d2_config_yaml='r2d2_config.yaml', shared_root='./r2d2-shared')

    # Invent backgrounds
    # MOM6 format: MOM.res.2019-04-15-01-00-00.nc MOM.res.2019-04-15-02-00-00.nc  MOM.res.2019-04-15-03-00-00.nc ...
    # CICE6 format: iced.2019-04-15-00000.nc iced.2019-04-15-03600.nc  iced.2019-04-15-07200.nc ...

    bkgdir = os.getenv('TESTDATA')
    ic_date = parser.parse("Apr 15 2018 09:00")
    bkg_date = ic_date
    for d in range(4):
        bkg_fname = './RESTART/MOM.res.'+bkg_date.strftime('%Y-%m-%d-%H-%M-%S')+'.nc'
        shutil.copyfile(os.path.join(bkgdir, 'MOM.res.nc'), bkg_fname, follow_symlinks=True)
        bkg_date += datetime.timedelta(hours=3)

    bkgstore = NiceDict({'start': '2018-04-15T09:00:00Z',
                         'end': '2018-04-15T18:00:00Z',
                         'source_dir': './RESTART',
                         'source_file_fmt': '{source_dir}/{file_type}.{year}-{month}-{day}-{hour}-00-00.nc',
                         'type': 'fc',
                         'forecast_steps': 'PT3H',
                         'experiment': 'soca',
                         'database': 'local',
                         'resolution': '72x35x25',
                         'step': 'PT3H',
                         'model': 'mom6_cice6_UFS',
                         'file_type': 'MOM.res'})

    ufsda.r2d2.store(bkgstore)
