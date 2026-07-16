from datetime import datetime, timedelta
from jedi import Jedi
from wxflow import AttrDict, Task, to_timedelta, add_to_datetime
from typing import Any, Dict

class TestGDASApp(Task):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Set fixed files for machine
        if machine == 'hera' or machine == 'ursa':
            _GDASAPP_TESTDATA = '/scratch3/NCEPDEV/da/role.jedipara/GDASApp/testdata'
            _FIXglobal        = '/scratch3/NCEPDEV/global/role.glopara/fix'
        elif machine == 'orion' or machine == 'hercules':
            _GDASAPP_TESTDATA = '/work2/noaa/da/role-da/GDASApp/testdata'
            _FIXglobal        = '/work2/noaa/global/role-global/fix'
        elif machine == 'wcoss2':
            _GDASAPP_TESTDATA = '/lfs/h2/emc/da/noscrub/emc.da/GDASApp/testdata'
            _FIXglobal        = '/lfs/h2/emc/global/noscrub/emc.global/FIX/fix'
        elif machine == 'gaeac6':
            _GDASAPP_TESTDATA = '/gpfs/f6/ira-sti/world-shared/GDASApp/testdata'
            _FIXglobal        = '/gpfs/f6/ira-sti/world-shared/GDASApp/fix'

        # Update task configuration
        self.task_config.update(AttrDict(
            {
                'WINDOW_BEGIN':       add_to_datetime(self.task_config.current_cycle, -to_timedelta(f"{self.task_config.assim_freq}H") / 2),
                'WINDOW_LENGTH':      'PT6H',
                'npz_anl':            127,
                'npx_anl':            49,
                'npy_anl':            49,
                'npz_his':            127,
                'npx_his':            49,
                'npy_his':            49,
                'npz_ges':            127,
                'npx_ges':            49,
                'npy_ges':            49,
                'layout_x':           1,
                'layout_y':           1,
                'layout_gsib_x':      3,
                'layout_gsib_y':      2,
                'NUMBER_OUTER_LOOPS': 2,
                'NINNER_LOOP1':       2,
                'NINNER_LOOP2':       4,
                'NMEM_ENS':           3,
                'STATICB_TYPE':       'identity',
                'GPREFIX':            'gdas.t12z',
                'OPREFIX':            'gdas.t18z',
                'GPREFIX_ENS':        'enkfgdas.t12z',
                'OPREFIX_ENS':        'enkfgdas.t18z',
                'berror_dir':         f"{_FIXglobal}/gdas/gsibec/C48",
                'fv3files_dir':       f"{_FIXglobal}/gdas/fv3jedi/fv3files",
                'crtm_dir':           f"{_FIXglobal}/crtm/2.4.0",
                'obs_dir':            f"{_GDASAPP_TESTDATA}/lowres/gdas.20210323/18/obs/atmos",
                'bias_dir':           f"{_GDASAPP_TESTDATA}/lowres/gdas.20210323/12/analysis/atmos/",
                'bkg_var_dir':        f"{_GDASAPP_TESTDATA}/lowres/gdas.20210323/12/model/atmos/history",
                'bkg_ens_dir':        lambda imem: f"{_GDASAPP_TESTDATA}/lowres/enkfgdas.20210323/12/{imem:03d}/model/atmos/history"
            }
        ))

        # Create dictionary of Jedi objects
        expected_keys = ['var']
        self.jedi_dict = Jedi.get_jedi_dict(self.task_config.jedi_config, self.task_config, expected_keys)

    def initialize(self):

        fh_dict = {'mkdir': [], 'copy_req': []}

        # Stage observation files
        self.task_config.jedi_dict['var'].stage_obsdatain(f"{self.task_config.obs_dir}")

        # Stage bias correction files
        self.task_config.jedi_dict['var'].stage_obsbiasin(self.task_config.bias_dir)

        # Stage background files
        sdir = f"{self.task_config.bkg_var_dir}"
        tdir = f"{self.task_config.jedi_dict['var'].RUNDIR}/bkg"
        fh_dict['mkdir'].append(tdir)
        fh_dict['copy_req'].append([f"{sdir}/{self.task_config.GPREFIX}csg_atm.f006.nc", f"{tdir}/{self.task_config.GPREFIX}cubed_sphere_grid_atmf006.nc"])
        fh_dict['copy_req'].append([f"{sdir}/{self.task_config.GPREFIX}csg_sfc.f006.nc", f"{tdir}/{self.task_config.GPREFIX}cubed_sphere_grid_sfcf006.nc"])

        # 
        for imem in range(1, self.task_config.NMEM_ENS+1):
            sdir = f"{self.task_config.bkg_ens_dir(imem)}"
            tdir = f"{self.task_config.jedi_dict['var'].RUNDIR}/ens/mem{imem:03d}"
            fh_dict['mkdir'].append(tdir)
            fh_dict['copy_req'].append([f"{sdir}/{self.task_config.GPREFIX}csg_atm.f006.nc", f"{tdir}/{self.task_config.GPREFIX}cubed_sphere_grid_atmf006.nc"])
            fh_dict['copy_req'].append([f"{sdir}/{self.task_config.GPREFIX}csg_sfc.f006.nc", f"{tdir}/{self.task_config.GPREFIX}cubed_sphere_grid_sfcf006.nc"])

        # Stage JEDI fix files
        sdir = f"{self.task_config.fv3files_dir}"
        tdir = f"{self.task_config.jedi_dict['var'].RUNDIR}/fv3jedi"
        fh_dict['mkdir'].append(tdir)
        fh_dict['copy_req'].append([f"{sdir}/akbk{self.task_config.npz}.nc4", f"{tdir}/akbk.nc4"])
        fh_dict['copy_req'].append([f"{sdir}/fmsmpp.nml",                     f"{tdir}/fmsmpp.nml"])
        fh_dict['copy_req'].append([f"{sdir}/field_table_gfdl",               f"{tdir}/field_table"])
        
        # Stage CRTM fix files
        sdir = f"{self.task_config.crtm_dir}"
        tdir = f"{self.task_config.jedi_dict['var'].RUNDIR}/crtm"
        fh_dict['mkdir'].append(tdir)
        for file in TestGDASApp.get_crtm_files():
            fh_dict['copy_req'].append([f"{sdir}/{file}", f"{tdir}/{file}"])

        # Stage background error files
        if self.task_config.STATICB_TYPE != 'identity':
            sdir = f"{self.task_config.berror_dir}"
            tdir = f"{self.task_config.jedi_dict['var'].RUNDIR}/berror"
            fh_dict['mkdir'].append(tdir)
            fh_dict['copy_req'].append([f"{sdir}/gfs_gsi_global.nml", f"{tdir}"])
            fh_dict['copy_req'].append([f"{sdir}/gsi-coeffs-gfs-global.nc", f"{tdir}"])

    def execute(self, jedi_dict_key: str) -> None:
        self.jedi_dict[jedi_dict_key].execute()

    def finalize(self) -> None:
        super.finalize()

    def clean(self) -> None:
        super().clean()

    @staticmethod
    def get_crtm_files():
        crtm_files = ['NPOESS.VISice.EmisCoeff', 'NPOESS.VISland.EmisCoeff', 'NPOESS.VISsnow.EmisCoeff', 'NPOESS.VISwater.EmisCoeff',
                      'NPOESS.IRice.EmisCoeff',  'NPOESS.IRland.EmisCoeff',  'NPOESS.IRsnow.EmisCoeff',
                      'Nalli.IRwater.EmisCoeff', 'FASTEM6.MWwater.EmisCoeff', 'AerosolCoeff', 'CloudCoeff',
                      'abi_g16.SpcCoeff',        'abi_g16.TauCoeff',
                      'abi_g17.SpcCoeff',        'abi_g17.TauCoeff',
                      'ahi_himawari8.SpcCoeff',  'ahi_himawari8.TauCoeff',
                      'ahi_himawari9.SpcCoeff',  'ahi_himawari9.TauCoeff',
                      'airs_aqua.SpcCoeff',      'airs_aqua.TauCoeff',
                      'amsr2_gcom-w1.SpcCoeff',  'amsr2_gcom-w1.TauCoeff',
                      'amsre_aqua.SpcCoeff',     'amsre_aqua.TauCoeff',
                      'amsua_aqua.SpcCoeff',     'amsua_aqua.TauCoeff',
                      'amsua_metop-a.SpcCoeff',  'amsua_metop-a.TauCoeff',
                      'amsua_metop-b.SpcCoeff',  'amsua_metop-b.TauCoeff',
                      'amsua_metop-c.SpcCoeff',  'amsua_metop-c.TauCoeff',
                      'amsua_n15.SpcCoeff',      'amsua_n15.TauCoeff',
                      'amsua_n18.SpcCoeff',      'amsua_n18.TauCoeff',
                      'amsua_n19.SpcCoeff',      'amsua_n19.TauCoeff',
                      'amsub_n17.SpcCoeff',      'amsub_n17.TauCoeff',
                      'atms_n20.SpcCoeff',       'atms_n20.TauCoeff',
                      'atms_npp.SpcCoeff',       'atms_npp.TauCoeff',
                      'avhrr3_metop-a.SpcCoeff', 'avhrr3_metop-a.TauCoeff',
                      'avhrr3_metop-b.SpcCoeff', 'avhrr3_metop-b.TauCoeff',
                      'avhrr3_metop-c.SpcCoeff', 'avhrr3_metop-c.TauCoeff',
                      'avhrr3_n18.SpcCoeff',     'avhrr3_n18.TauCoeff',
                      'avhrr3_n19.SpcCoeff',     'avhrr3_n19.TauCoeff',
                      'cris-fsr_n20.SpcCoeff',   'cris-fsr_n20.TauCoeff',
                      'cris-fsr_npp.SpcCoeff',   'cris-fsr_npp.TauCoeff',
                      'gmi_gpm.SpcCoeff',        'gmi_gpm.TauCoeff',
                      'hirs3_n17.SpcCoeff',      'hirs3_n17.TauCoeff',
                      'hirs4_metop-a.SpcCoeff',  'hirs4_metop-a.TauCoeff',
                      'hirs4_metop-b.SpcCoeff',  'hirs4_metop-b.TauCoeff',
                      'hirs4_n19.SpcCoeff',      'hirs4_n19.TauCoeff',
                      'iasi_metop-a.SpcCoeff',   'iasi_metop-a.TauCoeff',
                      'iasi_metop-b.SpcCoeff',   'iasi_metop-b.TauCoeff',
                      'iasi_metop-c.SpcCoeff',   'iasi_metop-c.TauCoeff',
                      'imgr_g11.SpcCoeff',       'imgr_g11.TauCoeff',
                      'imgr_g12.SpcCoeff',       'imgr_g12.TauCoeff',
                      'imgr_g13.SpcCoeff',       'imgr_g13.TauCoeff',
                      'imgr_g14.SpcCoeff',       'imgr_g14.TauCoeff',
                      'imgr_g15.SpcCoeff',       'imgr_g15.TauCoeff',
                      'mhs_metop-a.SpcCoeff',    'mhs_metop-a.TauCoeff',
                      'mhs_metop-b.SpcCoeff',    'mhs_metop-b.TauCoeff',
                      'mhs_metop-c.SpcCoeff',    'mhs_metop-c.TauCoeff',
                      'mhs_n18.SpcCoeff',        'mhs_n18.TauCoeff',
                      'mhs_n19.SpcCoeff',        'mhs_n19.TauCoeff',
                      'saphir_meghat.SpcCoeff',  'saphir_meghat.TauCoeff',
                      'seviri_m08.SpcCoeff',     'seviri_m08.TauCoeff',
                      'seviri_m09.SpcCoeff',     'seviri_m09.TauCoeff',
                      'seviri_m10.SpcCoeff',     'seviri_m10.TauCoeff',
                      'seviri_m11.SpcCoeff',     'seviri_m11.TauCoeff',
                      'sndrD1_g11.SpcCoeff',     'sndrD1_g11.TauCoeff',
                      'sndrD1_g12.SpcCoeff',     'sndrD1_g12.TauCoeff',
                      'sndrD1_g13.SpcCoeff',     'sndrD1_g13.TauCoeff',
                      'sndrD1_g14.SpcCoeff',     'sndrD1_g14.TauCoeff',
                      'sndrD1_g15.SpcCoeff',     'sndrD1_g15.TauCoeff',
                      'sndrD2_g11.SpcCoeff',     'sndrD2_g11.TauCoeff',
                      'sndrD2_g12.SpcCoeff',     'sndrD2_g12.TauCoeff',
                      'sndrD2_g13.SpcCoeff',     'sndrD2_g13.TauCoeff',
                      'sndrD2_g14.SpcCoeff',     'sndrD2_g14.TauCoeff',
                      'sndrD2_g15.SpcCoeff',     'sndrD2_g15.TauCoeff',
                      'sndrD3_g11.SpcCoeff',     'sndrD3_g11.TauCoeff',
                      'sndrD3_g12.SpcCoeff',     'sndrD3_g12.TauCoeff',
                      'sndrD3_g13.SpcCoeff',     'sndrD3_g13.TauCoeff',
                      'sndrD3_g14.SpcCoeff',     'sndrD3_g14.TauCoeff',
                      'sndrD3_g15.SpcCoeff',     'sndrD3_g15.TauCoeff',
                      'sndrD4_g11.SpcCoeff',     'sndrD4_g11.TauCoeff',
                      'sndrD4_g12.SpcCoeff',     'sndrD4_g12.TauCoeff',
                      'sndrD4_g13.SpcCoeff',     'sndrD4_g13.TauCoeff',
                      'sndrD4_g14.SpcCoeff',     'sndrD4_g14.TauCoeff',
                      'sndrD4_g15.SpcCoeff',     'sndrD4_g15.TauCoeff',
                      'ssmi_f15.SpcCoeff',       'ssmi_f15.TauCoeff',
                      'ssmis_f16.SpcCoeff',      'ssmis_f16.TauCoeff',
                      'ssmis_f17.SpcCoeff',      'ssmis_f17.TauCoeff',
                      'ssmis_f18.SpcCoeff',      'ssmis_f18.TauCoeff',
                      'ssmis_f19.SpcCoeff',      'ssmis_f19.TauCoeff',
                      'ssmis_f20.SpcCoeff',      'ssmis_f20.TauCoeff',
                      'viirs-m_j1.SpcCoeff',     'viirs-m_j1.TauCoeff',
                      'viirs-m_npp.SpcCoeff',    'viirs-m_npp.TauCoeff']

        return crtm_files
