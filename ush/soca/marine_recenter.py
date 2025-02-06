#!/usr/bin/env python3

from datetime import datetime, timedelta
import f90nml
from logging import getLogger
import os
from soca import bkg_utils
from typing import Dict
import ufsda
from ufsda.stage import soca_fix
import pygfs.utils.marine_da_utils as mdau
from wxflow import (AttrDict,
                    chdir,
                    Executable,
                    FileHandler,
                    logit,
                    parse_j2yaml,
                    Task,
                    add_to_datetime, to_timedelta,
                    WorkflowException)

logger = getLogger(__name__.split('.')[-1])


class MarineRecenter(Task):
    """
    Class for global ocean analysis recentering task
    """

    @logit(logger, name="MarineRecenter")
    def __init__(self, config: Dict) -> None:
        """Constructor for ocean recentering task
        Parameters:
        ------------
        config: Dict
            configuration, namely evironment variables
        Returns:
        --------
        None
        """

        logger.info("init")
        super().__init__(config)

        # Variables of convenience
        # TODO (AFE) maybe the g- vars should be done in the jjob
        PDY = self.task_config['PDY']
        cyc = self.task_config['cyc']
        DATA = self.task_config.DATA
        cdate = PDY + timedelta(hours=cyc)
        gdate = cdate - timedelta(hours=6)
        self.task_config['gcyc'] = gdate.strftime("%H")
        self.task_config['gPDY'] = datetime(gdate.year,
                                            gdate.month,
                                            gdate.day)

        gdas_home = os.path.join(config['HOMEgfs'], 'sorc', 'gdas.cd')

        half_assim_freq = timedelta(hours=int(config['assim_freq'])/2)
        window_begin = cdate - half_assim_freq
        window_end = cdate + half_assim_freq
        window_begin_iso = window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
        window_middle_iso = cdate.strftime('%Y-%m-%dT%H:%M:%SZ')
        berror_yaml_dir = os.path.join(gdas_home, 'parm', 'soca', 'berror')

        _window_begin = add_to_datetime(self.task_config.current_cycle, -to_timedelta(f"{self.task_config.assim_freq}H") / 2)
        _window_end = add_to_datetime(self.task_config.current_cycle, to_timedelta(f"{self.task_config.assim_freq}H") / 2)
        _enspert_relpath = os.path.relpath(self.task_config.DATAens, self.task_config.DATA)

        local_dict = AttrDict({'window_begin': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
                               'PARMsoca': os.path.join(self.task_config.PARMgfs, 'gdas', 'soca'),
                               'MARINE_WINDOW_BEGIN': _window_begin,
                               'MARINE_WINDOW_BEGIN_ISO': _window_begin.strftime('%Y-%m-%dT%H:%M:%SZ'),
                               'MARINE_WINDOW_END': _window_end,
                               'MARINE_WINDOW_END_ISO': _window_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                               'MARINE_WINDOW_LENGTH': f"PT{self.task_config['assim_freq']}H",
                               'MARINE_WINDOW_MIDDLE': self.task_config.current_cycle,
                               'MARINE_WINDOW_MIDDLE_ISO': self.task_config.current_cycle.strftime('%Y-%m-%dT%H:%M:%SZ'),
                               'DATA': DATA,
                               'dump': self.task_config.RUN,
                               'stage_dir': DATA,
                               'soca_input_fix_dir': self.task_config.SOCA_INPUT_FIX_DIR,
                               'NMEM_ENS': self.task_config.NMEM_ENS,
                               'GDUMP_ENS': self.task_config.GDUMP_ENS,
                               'ENSPERT_RELPATH': _enspert_relpath,
                               'MARINE_WINDOW_LENGTH': f"PT{config['assim_freq']}H",
                               'recen_yaml_template': os.path.join(berror_yaml_dir, 'soca_ensrecenter.yaml'),
                               'recen_yaml_file': os.path.join(DATA, 'soca_ensrecenter.yaml'),
                               'gridgen_yaml': os.path.join(gdas_home, 'parm', 'soca', 'gridgen', 'gridgen.yaml'),
                               'BKG_LIST': 'bkg_list.yaml',
                               'window_begin': window_begin,
                               'bkg_dir': os.path.join(DATA, 'bkg'),
                               'INPUT': os.path.join(DATA, 'INPUT'),
                               'ens_dir': os.path.join(DATA, 'ens')})

        # Extend task_config with local_dict
        self.task_config.update(local_dict)

    @logit(logger)
    def initialize(self):
        """Method initialize for ocean recentering task
        Parameters:
        ------------
        None
        Returns:
        --------
        None
        """

        logger.info("initialize")
        RUN = self.task_config.RUN
        gcyc = self.task_config.gcyc

        # stage fix files
        logger.info(f"Staging SOCA fix files from {self.task_config.SOCA_INPUT_FIX_DIR}")
        soca_fix_list = parse_j2yaml(self.task_config.SOCA_FIX_YAML_TMPL, self.task_config)
        FileHandler(soca_fix_list).sync()

        # prepare the MOM6 input.nml
        mdau.prep_input_nml(self.task_config)

        # stage the soca utility yamls (gridgen, fields and ufo mapping yamls)
        logger.info(f"Staging SOCA utility yaml files from {self.task_config.PARMsoca}")
        soca_utility_list = parse_j2yaml(self.task_config.MARINE_UTILITY_YAML_TMPL, self.task_config)
        FileHandler(soca_utility_list).sync()

        # stage backgrounds
        bkg_list = parse_j2yaml(self.task_config.MARINE_DET_STAGE_BKG_YAML_TMPL, self.task_config)
        FileHandler(bkg_list).sync()
        # stage ensemble backgrounds for soca2cice
        ens_bkg_list = parse_j2yaml(self.task_config.MARINE_ENSDA_STAGE_BKG_YAML_TMPL, self.task_config)
        FileHandler(ens_bkg_list).sync()

#        ################################################################################
#        # Copy initial condition
#
#        bkg_utils.stage_ic(self.task_config.bkg_dir, self.task_config.DATA, gcyc)
#
        ################################################################################
        # stage ensemble members
        logger.info("---------------- Stage ensemble members")
        FileHandler({'mkdir': [self.task_config.ens_dir]}).sync()
        nmem_ens = self.task_config.NMEM_ENS
        gPDYstr = self.task_config.gPDY.strftime("%Y%m%d")
        ens_member_list = []
        for mem in range(1, nmem_ens+1):
            for domain in ['ocean', 'ice']:
                mem_dir = os.path.join(self.task_config.ROTDIR,
                                       f'enkf{RUN}.{gPDYstr}',
                                       f'{gcyc}',
                                       f'mem{str(mem).zfill(3)}',
                                       'model',
                                       domain,
                                       'history')
                mem_dir_real = os.path.realpath(mem_dir)
                f00 = f"enkf{RUN}.{domain}.t{gcyc}z.inst.f009.nc"

                fname_in = os.path.abspath(os.path.join(mem_dir_real, f00))
                fname_out = os.path.realpath(os.path.join(self.task_config.ens_dir,
                                             domain+"."+str(mem)+".nc"))
                ens_member_list.append([fname_in, fname_out])

        FileHandler({'copy': ens_member_list}).sync()
        # stage ensemble ice restarts
        # make a copy of the CICE6 restart
        logger.info("---------------- Stage ensemble CICE restarts")
        # set the restart date, dependent on the cycling type
        if self.task_config.DOIAU:
            # forecast initialized at the begining of the DA window
            fcst_begin = self.task_config.MARINE_WINDOW_BEGIN_ISO
            rst_date = self.task_config.MARINE_WINDOW_BEGIN.strftime('%Y%m%d.%H%M%S')
        else:
            # forecast initialized at the middle of the DA window
            fcst_begin = self.task_config.MARINE_WINDOW_MIDDLE_ISO
            rst_date = self.task_config.MARINE_WINDOW_MIDDLE.strftime('%Y%m%d.%H%M%S')
        ens_cice_list = []
        for mem in range(1, nmem_ens+1):
            mem_dir = os.path.join(self.task_config.ROTDIR,
                                   f'enkf{RUN}.{gPDYstr}',
                                   f'{gcyc}',
                                   f'mem{str(mem).zfill(3)}',
                                   'model',
                                   'ice',
                                   'restart')
            mem_dir_real = os.path.realpath(mem_dir)
            f00 = f'{rst_date}.cice_model.res.nc'
            fname_in = os.path.abspath(os.path.join(mem_dir_real, f00))
            fname_out = os.path.realpath(os.path.join(self.task_config.ens_dir,
                                         "cice_model.res."+str(mem)+".nc"))
            ens_cice_list.append([fname_in, fname_out])
            fname_out = os.path.realpath(os.path.join(self.task_config.ens_dir,
                                         "cice_model.res.output."+str(mem)+".nc"))
            ens_cice_list.append([fname_in, fname_out])
        FileHandler({'copy': ens_cice_list}).sync()

        ################################################################################
        # generate the YAML file for recenterer

        logger.info(f"---------------- generate soca_ensrecenter.yaml")

        recen_yaml = parse_j2yaml(self.task_config.recen_yaml_template, self.task_config)
        recen_yaml.save(self.task_config.recen_yaml_file)

    @logit(logger)
    def run(self):
        """Method run for ocean recentering task
        Parameters:
        ------------
        None
        Returns:
        --------
        None
        """

        logger.info("run")

        chdir(self.task_config.DATA)

        exec_cmd_gridgen = Executable(self.task_config.APRUN_OCNANALECEN)
        exec_name_gridgen = os.path.join(self.task_config.EXECgfs, 'gdas_soca_gridgen.x')
        exec_cmd_gridgen.add_default_arg(exec_name_gridgen)
        exec_cmd_gridgen.add_default_arg(self.task_config.gridgen_yaml)

        try:
            logger.debug(f"Executing {exec_cmd_gridgen}")
            exec_cmd_gridgen()
        except OSError:
            raise OSError(f"Failed to execute {exec_cmd_gridgen}")
        except Exception:
            raise WorkflowException(f"An error occured during execution of {exec_cmd_gridgen}")
        pass

        exec_cmd_recen = Executable(self.task_config.APRUN_OCNANALECEN)
        exec_name_recen = os.path.join(self.task_config.EXECgfs, 'gdas_ens_handler.x')
        exec_cmd_recen.add_default_arg(exec_name_recen)
        exec_cmd_recen.add_default_arg(os.path.basename(self.task_config.recen_yaml_file))

        try:
            logger.debug(f"Executing {exec_cmd_recen}")
            exec_cmd_recen()
        except OSError:
            raise OSError(f"Failed to execute {exec_cmd_recen}")
        except Exception:
            raise WorkflowException(f"An error occured during execution of {exec_cmd_recen}")
        pass

    @logit(logger)
    def finalize(self):
        """Method finalize for ocean recentering task
        Parameters:
        ------------
        None
        Returns:
        --------
        None
        """

        logger.info("finalize")

        RUN = self.task_config.RUN
        cyc = str(self.task_config.cyc).zfill(2)
        incr_file = f'enkf{RUN}.t{cyc}z.ocninc.nc'
        nmem_ens = self.task_config.NMEM_ENS
        PDYstr = self.task_config.PDY.strftime("%Y%m%d")
        mem_dir_list = []
        copy_list = []

        # Copy the recentering increment files to the member COMROOT directories
        for mem in range(1, nmem_ens+1):
            mem_dir = os.path.join(self.task_config.ROTDIR,
                                   f'enkf{RUN}.{PDYstr}',
                                   f'{cyc}',
                                   f'mem{str(mem).zfill(3)}',
                                   'analysis',
                                   'ocean')
            mem_dir_real = os.path.realpath(mem_dir)
            mem_dir_list.append(mem_dir_real)
            copy_list.append([f'ocn.recenter.incr.{str(mem)}.nc',
                              os.path.join(mem_dir_real, incr_file)])

        FileHandler({'mkdir': mem_dir_list}).sync()
        FileHandler({'copy': copy_list}).sync()

        # Copy the CICE restart files to the member COMROOT directories
        if os.getenv('DOIAU') == "YES":
            cice_rst_date = self.task_config.MARINE_WINDOW_BEGIN.strftime('%Y%m%d.%H%M%S')
        else:
            cice_rst_date = cdate.strftime('%Y%m%d.%H%M%S')
        mem_dir_list = []
        copy_list = []
        for mem in range(1, nmem_ens+1):
            mem_dir = os.path.join(self.task_config.ROTDIR,
                                   f'enkf{RUN}.{PDYstr}',
                                   f'{cyc}',
                                   f'mem{str(mem).zfill(3)}',
                                   'analysis',
                                   'ice')
            mem_dir_real = os.path.realpath(mem_dir)
            mem_dir_list.append(mem_dir_real)
            copy_list.append([f'ens/cice_model.res.output.{str(mem)}.nc',
                              os.path.join(mem_dir_real, f'{cice_rst_date}.cice_model_anl.res.nc')])
        FileHandler({'mkdir': mem_dir_list}).sync()
        FileHandler({'copy': copy_list}).sync()
