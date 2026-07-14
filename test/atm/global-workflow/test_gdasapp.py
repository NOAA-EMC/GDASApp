import os
from datetime import datetime, timedelta
from jedi import Jedi
from wxflow import AttrDict, Task

class TestGDASApp(Task):
    def __init__(self):
        super().__init__()

        _prev = datetime.strptime('2021032318', '%Y%m%d%H') - timedelta(hours=6)

        self.task_config.update(AttrDict(
            {
                'PSLOT': 'gdas_test',
                'EXPDIR': os.path.join(bindir, 'test/atm/global-workflow/testrun/experiments', 'gdas_test'),
                'ROTDIR': os.path.join(bindir, 'test/atm/global-workflow/testrun/ROTDIRS', 'gdas_test'),
                'DATAROOT': os.path.join(bindir, 'test/atm/global-workflow/testrun/RUNDIRS', 'gdas_test'),
                'COMROOT': os.path.join(bindir, 'test/atm/global-workflow/testrun/RUNDIRS', 'gdas_test'),
                'PDY': '20210323',
                'cyc': '18',
                'gPDY': _prev.strftime('%Y%m%d'),
                'gcyc': _prev.strftime('%H'),
                'RUN': 'gdas',
                'CDUMP': 'gdas',
                'GDUMP': 'gdas',
                'GPREFIX': f"gdas.t{_prev.strftime('%H')}z",
                'OPREFIX': f"gdas.t18z",
                'pid': os.environ.get('pid', str(os.getpid())),
                'jobid': os.environ.get('pid', str(os.getpid())),
                'NMEM_ENS': 3,
                'ACCOUNT': 'da-cpu',
                'COMIN_OBS': os.path.join(bindir, 'test/atm/global-workflow/testrun/ROTDIRS', 'gdas_test', 'gdas.20210323', '18', 'obs'),
                'COMIN_ATMOS_ANALYSIS_PREV': os.path.join(bindir, 'test/atm/global-workflow/testrun/ROTDIRS', 'gdas_test', f"gdas.{_prev.strftime('%Y%m%d')}", _prev.strftime('%H'), 'analysis', 'atmos'),
                'COMIN_ATMOS_HISTORY_PREV': os.path.join(bindir, 'test/atm/global-workflow/testrun/ROTDIRS', 'gdas_test', f"gdas.{_prev.strftime('%Y%m%d')}", _prev.strftime('%H'), 'model', 'atmos', 'history')
            }
        ))

        # Create dictionary of Jedi objects
        expected_keys = ['var']
        self.jedi_dict = Jedi.get_jedi_dict(self.task_config.jedi_config, self.task_config, expected_keys)

    def initialize(self):

        fh_dict = {'mkdir': [], 'copy_req': []}

        dpath_root = f"{self.task_config.GDASAPP_TESTDATA}/lowres"

        # Stage observation files
        logger.info(f"Staging observation files")
        self.task_config.jedi_dict['var'].stage_obsdatain(f"{self.task_config.COMIN_OBS}/atmos")

        # Stage bias correction files
        logger.info(f"Staging bias correction files")
        self.task_config.jedi_dict['var'].stage_obsbiasin(self.task_config.COMIN_ATMOS_ANALYSIS_PREV)

        # History files
        dpath = f"gdas.{self.task_config.gPDY}/{self.task_config.gcyc}/model/atmos/history"
        flist = ['atmf006.nc', 'csg_atm.f006.nc', 'csg_sfc.f006.nc']
        for file in flist:
            source = f"{dpath_root}/{dpath}/{self.task_config.GPREFIX}.{file}"
            target = f"{self.task_config.jedi_dict['var'].RUNDIR}/bkg"

            fh_dict['copy_req'].append([source, target])

        # 
        for imem in range(1, self.task_config.NMEM_ENS+1):
            flist = ['atmf006.nc', 'csg_atm.f006.nc', 'csg_sfc.f006.nc']
            for file in flist:
                source = f"{dpath_root}/enkfgdas.{self.task_config.gPDY}/{self.task_config.gcyc}/{imem:03d}/model/atmos/history/"
                target = f"{self.task_config.jedi_dict['var'].RUNDIR}/ens/mem{imem:03d}"

                fh_dict['mkdir'].append(target)
                fh_dict['copy_req'].append([f"{source}", f"{target}"])

            source = f"{dpath_root}/enkfgdas.{self.task_config.gPDY}/{self.task_config.gcyc}/{imem:03d}/model/atmos/history"
            target = f"{self.task_config.ROTDIR}/enkf.{self.task_config.GDUMP}.{self.task_config.gPDY}/{self.task_config.gcyc}/{imem:03d}/model/atmos/history"
            fh_dict['copy_req'].append([source, target])
        

