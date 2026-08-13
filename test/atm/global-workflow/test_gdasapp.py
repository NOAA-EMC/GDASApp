from datetime import datetime, timedelta
from jedi import Jedi
from wxflow import AttrDict, Task, to_timedelta, add_to_datetime
from typing import Any, Dict

class varGDAS(Task):
    def __init__(self, config: Dict[str, Any]):
        # Make sure Task class constructor gets PDY, cyc, and assim_freq from config,
        # and make sure the current constructor gets MACHINE ID
        for key in ['PDY', 'cyc', 'assim_freq',
                    'MACHINE_ID']:
            if key not in config:
                raise KeyError(f"config is missing required key: '{key}'")

        super().__init__(config)

        # Set fixed files for this MACHINE_ID
        if self.task_config.MACHINE_ID in ['hera', 'ursa']:
            _GDASAPP_TESTDATA = '/scratch3/NCEPDEV/da/role.jedipara/GDASApp/testdata'
            _FIXglobal        = '/scratch3/NCEPDEV/global/role.glopara/fix'
        elif self.task_config.MACHINE_ID in ['orion', 'hercules']:
            _GDASAPP_TESTDATA = '/work2/noaa/da/role-da/gdasApp/testdata'
            _FIXglobal        = '/work2/noaa/global/role-global/fix'
        elif self.task_config.MACHINE_ID == 'wcoss2':
            _GDASAPP_TESTDATA = '/lfs/h2/emc/da/noscrub/emc.da/GDASApp/testdata'
            _FIXglobal        = '/lfs/h2/emc/global/noscrub/emc.global/FIX/fix'
        elif self.task_config.MACHINE_ID == 'gaeac6':
            _GDASAPP_TESTDATA = '/gpfs/f6/ira-sti/world-shared/GDASApp/testdata'
            _FIXglobal        = '/gpfs/f6/ira-sti/world-shared/GDASApp/fix'

        # Various intermediate parameters
        _npz = 127
        _npx = 49
        _npy = 49
        _layout_x = 1
        _layout_y = 1

        # Update task configuration
        self.task_config.update(AttrDict(
            {
                # Configurable parameters
                'NMEM_ENS':                     3,
                'NUMBER_OUTER_LOOPS':           2,
                'NINNER_LOOP1':                 2,
                'NINNER_LOOP2':                 4,
                'STATICB_TYPE':                 'identity',
                'layout_x':                     _layout_x,
                'layout_y':                     _layout_y,
                # File prefixes
                'GPREFIX':                      'gdas.t12z',
                'OPREFIX':                      'gdas.t18z',
                'GPREFIX_ENS':                  'enkfgdas.t12z',
                'OPREFIX_ENS':                  'enkfgdas.t18z',
                # Data directories
                'CRTM_FIX':                     f"{_FIXglobal}/crtm/2.4.0",
                'BERROR_FIX':                   f"{_FIXglobal}/gdas/gsibec/C48",
                'FV3FILES_FIX':                 f"{_FIXglobal}/gdas/fv3jedi/fv3files",
                'COMIN_OBS':                    f"{_GDASAPP_TESTDATA}/lowres/gdas.20210323/18/obs/atmos",
                'COMIN_ATMOS_ANALYSIS_PREV':    f"{_GDASAPP_TESTDATA}/lowres/gdas.20210323/12/analysis/atmos/",
                'COMIN_ATMOS_HISTORY_PREV':     f"{_GDASAPP_TESTDATA}/lowres/gdas.20210323/12/model/atmos/history",
                'COMIN_ATMOS_HISTORY_PREV_ENS': lambda imem: f"{_GDASAPP_TESTDATA}/lowres/enkfgdas.20210323/12/mem{imem:03d}/model/atmos/history",
                # Non-configurable parameters
                'npz_anl':                      _npz,
                'npx_anl':                      _npx,
                'npy_anl':                      _npy,
                'npz_his':                      _npz,
                'npx_his':                      _npx,
                'npy_his':                      _npy,
                'npz_ges':                      _npz,
                'npx_ges':                      _npx,
                'npy_ges':                      _npy,
                'WINDOW_BEGIN':                 add_to_datetime(self.task_config.current_cycle, -to_timedelta(f"{self.task_config.assim_freq}H") / 2),
                'WINDOW_LENGTH':                f"PT{self.task_config.assim_freq}H",
                'layout_gsib_x':                3 * _layout_x,
                'layout_gsib_y':                2 * _layout_y,
            }
        ))

        # Set JEDI configuration dictionary
        self.jedi_config = {
            '3dvar': {
                'rundir': '/scratch3/NCEPDEV/da/David.New/test_gdasapp',
                'exe_src': '{{ HOMEgdas }}/exec/gdas.x',
                'jedi_args': ['fv3jedi', 'variational'],
                'jcb_algo': '3dvar',
                'obs_list': ['radiance_amsua_n19',
                             'sondes'],
                'app_test': {
                    'do_testing': True,
                    'test_reference_filename': '{{ HOMEgdas }}/test/testreference/atm_jjob_3dvar.ref',
                    'test_output_filename': '{{ HOMEgdas }}/build/gdas/test/testoutput/atm_jjob_3dvar.test.out',
                    'test_float_relative_tolerance': 1.0e-3,
                    'test_float_absolute_tolerance': 1.0e-5
                }
            }
        }

        # Create dictionary of Jedi objects
        expected_keys = ['3dvar']
        self.jedi_dict = Jedi.get_jedi_dict(self.task_config.jedi_config, self.task_config, expected_keys)

    def initialize(self):

        fh_dict = {'mkdir': [], 'copy_req': []}

        # Stage observation files
        self.jedi_dict['3dvar'].stage_obsdatain(self.task_config.COMIN_OBS)

        # Stage bias correction files
        self.jedi_dict['3dvar'].stage_obsbiasin(self.task_config.COMIN_ATMOS_ANALYSIS_PREV)

        # Stage background files
        sdir = f"{self.task_config.COMIN_ATMOS_HISTORY_PREV}"
        tdir = f"{self.jedi_dict['3dvar'].jcb_config.atmosphere_background_path}"
        fh_dict['mkdir'].append(tdir)
        fh_dict['copy_req'].append([f"{sdir}/{self.task_config.GPREFIX}csg_atm.f006.nc", f"{tdir}/{self.task_config.GPREFIX}cubed_sphere_grid_atmf006.nc"])
        fh_dict['copy_req'].append([f"{sdir}/{self.task_config.GPREFIX}csg_sfc.f006.nc", f"{tdir}/{self.task_config.GPREFIX}cubed_sphere_grid_sfcf006.nc"])

        # 
        for imem in range(1, self.task_config.NMEM_ENS+1):
            sdir = f"{self.task_config.COMIN_ATMOS_HISTORY_PREV_ENS(imem)}"
            tdir = f"{self.jedi_dict['3dvar'].RUNDIR}/ens/mem{imem:03d}"
            fh_dict['mkdir'].append(tdir)
            fh_dict['copy_req'].append([f"{sdir}/{self.task_config.GPREFIX}csg_atm.f006.nc", f"{tdir}/{self.task_config.GPREFIX}cubed_sphere_grid_atmf006.nc"])
            fh_dict['copy_req'].append([f"{sdir}/{self.task_config.GPREFIX}csg_sfc.f006.nc", f"{tdir}/{self.task_config.GPREFIX}cubed_sphere_grid_sfcf006.nc"])

        # Stage JEDI fix files
        sdir = f"{self.task_config.FV3FILES_FIX}"
        tdir = f"{self.jedi_dict['3dvar'].jcb_config.atmosphere_fv3jedi_files_path}"
        fh_dict['mkdir'].append(tdir)
        fh_dict['copy_req'].append([f"{sdir}/akbk{self.task_config.npz_anl}.nc4", f"{tdir}/akbk.nc4"])
        fh_dict['copy_req'].append([f"{sdir}/fmsmpp.nml",                         f"{tdir}/fmsmpp.nml"])
        fh_dict['copy_req'].append([f"{sdir}/field_table_gfdl",                   f"{tdir}/field_table"])
        
        # Stage CRTM fix files
        sdir = f"{self.task_config.CRTM_FIX}"
        tdir = f"{self.jedi_dict['3dvar'].jcb_config.crtm_coefficient_path}"
        fh_dict['mkdir'].append(tdir)
        for file in varGDAS.get_crtm_files():
            fh_dict['copy_req'].append([f"{sdir}/{file}", f"{tdir}/{file}"])

        # Stage background error files
        if self.task_config.STATICB_TYPE != 'identity':
            sdir = f"{self.task_config.BERROR_FIX}"
            tdir = f"{self.jedi_dict['3dvar'].jcb_config.atmosphere_gsibec_path}"
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
        crtm_files = ['NPOESS.VISice.EmisCoeff.bin', 'NPOESS.VISland.EmisCoeff.bin', 'NPOESS.VISsnow.EmisCoeff.bin', 'NPOESS.VISwater.EmisCoeff.bin',
                      'NPOESS.IRice.EmisCoeff.bin',  'NPOESS.IRland.EmisCoeff.bin',  'NPOESS.IRsnow.EmisCoeff.bin',
                      'Nalli.IRwater.EmisCoeff.bin', 'FASTEM6.MWwater.EmisCoeff.bin', 'AerosolCoeff.bin', 'CloudCoeff.bin',
                      'abi_g16.SpcCoeff.bin',        'abi_g16.TauCoeff.bin',
                      'abi_g17.SpcCoeff.bin',        'abi_g17.TauCoeff.bin',
                      'ahi_himawari8.SpcCoeff.bin',  'ahi_himawari8.TauCoeff.bin',
                      'ahi_himawari9.SpcCoeff.bin',  'ahi_himawari9.TauCoeff.bin',
                      'airs_aqua.SpcCoeff.bin',      'airs_aqua.TauCoeff.bin',
                      'amsr2_gcom-w1.SpcCoeff.bin',  'amsr2_gcom-w1.TauCoeff.bin',
                      'amsre_aqua.SpcCoeff.bin',     'amsre_aqua.TauCoeff.bin',
                      'amsua_aqua.SpcCoeff.bin',     'amsua_aqua.TauCoeff.bin',
                      'amsua_metop-a.SpcCoeff.bin',  'amsua_metop-a.TauCoeff.bin',
                      'amsua_metop-b.SpcCoeff.bin',  'amsua_metop-b.TauCoeff.bin',
                      'amsua_metop-c.SpcCoeff.bin',  'amsua_metop-c.TauCoeff.bin',
                      'amsua_n15.SpcCoeff.bin',      'amsua_n15.TauCoeff.bin',
                      'amsua_n18.SpcCoeff.bin',      'amsua_n18.TauCoeff.bin',
                      'amsua_n19.SpcCoeff.bin',      'amsua_n19.TauCoeff.bin',
                      'amsub_n17.SpcCoeff.bin',      'amsub_n17.TauCoeff.bin',
                      'atms_n20.SpcCoeff.bin',       'atms_n20.TauCoeff.bin',
                      'atms_npp.SpcCoeff.bin',       'atms_npp.TauCoeff.bin',
                      'avhrr3_metop-a.SpcCoeff.bin', 'avhrr3_metop-a.TauCoeff.bin',
                      'avhrr3_metop-b.SpcCoeff.bin', 'avhrr3_metop-b.TauCoeff.bin',
                      'avhrr3_metop-c.SpcCoeff.bin', 'avhrr3_metop-c.TauCoeff.bin',
                      'avhrr3_n18.SpcCoeff.bin',     'avhrr3_n18.TauCoeff.bin',
                      'avhrr3_n19.SpcCoeff.bin',     'avhrr3_n19.TauCoeff.bin',
                      'cris-fsr_n20.SpcCoeff.bin',   'cris-fsr_n20.TauCoeff.bin',
                      'cris-fsr_npp.SpcCoeff.bin',   'cris-fsr_npp.TauCoeff.bin',
                      'gmi_gpm.SpcCoeff.bin',        'gmi_gpm.TauCoeff.bin',
                      'hirs3_n17.SpcCoeff.bin',      'hirs3_n17.TauCoeff.bin',
                      'hirs4_metop-a.SpcCoeff.bin',  'hirs4_metop-a.TauCoeff.bin',
                      'hirs4_metop-b.SpcCoeff.bin',  'hirs4_metop-b.TauCoeff.bin',
                      'hirs4_n19.SpcCoeff.bin',      'hirs4_n19.TauCoeff.bin',
                      'iasi_metop-a.SpcCoeff.bin',   'iasi_metop-a.TauCoeff.bin',
                      'iasi_metop-b.SpcCoeff.bin',   'iasi_metop-b.TauCoeff.bin',
                      'iasi_metop-c.SpcCoeff.bin',   'iasi_metop-c.TauCoeff.bin',
                      'imgr_g11.SpcCoeff.bin',       'imgr_g11.TauCoeff.bin',
                      'imgr_g12.SpcCoeff.bin',       'imgr_g12.TauCoeff.bin',
                      'imgr_g13.SpcCoeff.bin',       'imgr_g13.TauCoeff.bin',
                      'imgr_g14.SpcCoeff.bin',       'imgr_g14.TauCoeff.bin',
                      'imgr_g15.SpcCoeff.bin',       'imgr_g15.TauCoeff.bin',
                      'mhs_metop-a.SpcCoeff.bin',    'mhs_metop-a.TauCoeff.bin',
                      'mhs_metop-b.SpcCoeff.bin',    'mhs_metop-b.TauCoeff.bin',
                      'mhs_metop-c.SpcCoeff.bin',    'mhs_metop-c.TauCoeff.bin',
                      'mhs_n18.SpcCoeff.bin',        'mhs_n18.TauCoeff.bin',
                      'mhs_n19.SpcCoeff.bin',        'mhs_n19.TauCoeff.bin',
                      'saphir_meghat.SpcCoeff.bin',  'saphir_meghat.TauCoeff.bin',
                      'seviri_m08.SpcCoeff.bin',     'seviri_m08.TauCoeff.bin',
                      'seviri_m09.SpcCoeff.bin',     'seviri_m09.TauCoeff.bin',
                      'seviri_m10.SpcCoeff.bin',     'seviri_m10.TauCoeff.bin',
                      'seviri_m11.SpcCoeff.bin',     'seviri_m11.TauCoeff.bin',
                      'sndrD1_g11.SpcCoeff.bin',     'sndrD1_g11.TauCoeff.bin',
                      'sndrD1_g12.SpcCoeff.bin',     'sndrD1_g12.TauCoeff.bin',
                      'sndrD1_g13.SpcCoeff.bin',     'sndrD1_g13.TauCoeff.bin',
                      'sndrD1_g14.SpcCoeff.bin',     'sndrD1_g14.TauCoeff.bin',
                      'sndrD1_g15.SpcCoeff.bin',     'sndrD1_g15.TauCoeff.bin',
                      'sndrD2_g11.SpcCoeff.bin',     'sndrD2_g11.TauCoeff.bin',
                      'sndrD2_g12.SpcCoeff.bin',     'sndrD2_g12.TauCoeff.bin',
                      'sndrD2_g13.SpcCoeff.bin',     'sndrD2_g13.TauCoeff.bin',
                      'sndrD2_g14.SpcCoeff.bin',     'sndrD2_g14.TauCoeff.bin',
                      'sndrD2_g15.SpcCoeff.bin',     'sndrD2_g15.TauCoeff.bin',
                      'sndrD3_g11.SpcCoeff.bin',     'sndrD3_g11.TauCoeff.bin',
                      'sndrD3_g12.SpcCoeff.bin',     'sndrD3_g12.TauCoeff.bin',
                      'sndrD3_g13.SpcCoeff.bin',     'sndrD3_g13.TauCoeff.bin',
                      'sndrD3_g14.SpcCoeff.bin',     'sndrD3_g14.TauCoeff.bin',
                      'sndrD3_g15.SpcCoeff.bin',     'sndrD3_g15.TauCoeff.bin',
                      'sndrD4_g11.SpcCoeff.bin',     'sndrD4_g11.TauCoeff.bin',
                      'sndrD4_g12.SpcCoeff.bin',     'sndrD4_g12.TauCoeff.bin',
                      'sndrD4_g13.SpcCoeff.bin',     'sndrD4_g13.TauCoeff.bin',
                      'sndrD4_g14.SpcCoeff.bin',     'sndrD4_g14.TauCoeff.bin',
                      'sndrD4_g15.SpcCoeff.bin',     'sndrD4_g15.TauCoeff.bin',
                      'ssmi_f15.SpcCoeff.bin',       'ssmi_f15.TauCoeff.bin',
                      'ssmis_f16.SpcCoeff.bin',      'ssmis_f16.TauCoeff.bin',
                      'ssmis_f17.SpcCoeff.bin',      'ssmis_f17.TauCoeff.bin',
                      'ssmis_f18.SpcCoeff.bin',      'ssmis_f18.TauCoeff.bin',
                      'ssmis_f19.SpcCoeff.bin',      'ssmis_f19.TauCoeff.bin',
                      'ssmis_f20.SpcCoeff.bin',      'ssmis_f20.TauCoeff.bin',
                      'viirs-m_j1.SpcCoeff.bin',     'viirs-m_j1.TauCoeff.bin',
                      'viirs-m_npp.SpcCoeff.bin',    'viirs-m_npp.TauCoeff.bin']

        return crtm_files
