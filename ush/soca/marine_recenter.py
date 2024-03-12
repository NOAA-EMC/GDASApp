#!/usr/bin/env python3

from datetime import datetime, timedelta
import f90nml
from logging import getLogger
import os
from soca import bkg_utils
from typing import Dict
import ufsda
from ufsda.stage import soca_fix
from wxflow import (AttrDict,
                    chdir,
                    Executable,
                    FileHandler,
                    logit,
                    parse_j2yaml,
                    Task,
                    Template,
                    TemplateConstants,
                    WorkflowException,
                    YAMLFile)

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
        PDY = self.runtime_config['PDY']
        cyc = self.runtime_config['cyc']
        DATA = self.runtime_config.DATA
        cdate = PDY + timedelta(hours=cyc)
        gdate = cdate - timedelta(hours=6)
        self.runtime_config['gcyc'] = gdate.strftime("%H")
        self.runtime_config['gPDY'] = datetime(gdate.year,
                                               gdate.month,
                                               gdate.day)

        gdas_home = os.path.join(config['HOMEgfs'], 'sorc', 'gdas.cd')

        half_assim_freq = timedelta(hours=int(config['assim_freq'])/2)
        window_begin = cdate - half_assim_freq
        window_begin_iso = window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
        window_middle_iso = cdate.strftime('%Y-%m-%dT%H:%M:%SZ')

        self.recen_config = AttrDict(
            {'window_begin': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
             'ATM_WINDOW_BEGIN': window_begin_iso,
             'ATM_WINDOW_MIDDLE': window_middle_iso,
             'DATA': DATA,
             'dump': self.runtime_config.RUN,
             'fv3jedi_stage_files': self.config.FV3JEDI_STAGE_YAML,
             'fv3jedi_stage': self.config.FV3JEDI_STAGE_YAML,
             'stage_dir': DATA,
             'soca_input_fix_dir': self.config.SOCA_INPUT_FIX_DIR,
             'NMEM_ENS': self.config.NMEM_ENS,
             'ATM_WINDOW_LENGTH': f"PT{config['assim_freq']}H"})

        berror_yaml_dir = os.path.join(gdas_home, 'parm', 'soca', 'berror')
        self.config['recen_yaml_template'] = os.path.join(berror_yaml_dir, 'soca_ensrecenter.yaml')
        self.config['recen_yaml_file'] = os.path.join(DATA, 'soca_ensrecenter.yaml')
        self.config['gridgen_yaml'] = os.path.join(gdas_home, 'parm', 'soca', 'gridgen', 'gridgen.yaml')
        self.config['BKG_LIST'] = 'bkg_list.yaml'
        self.config['window_begin'] = window_begin
        self.config['mom_input_nml_src'] = os.path.join(gdas_home, 'parm', 'soca', 'fms', 'input.nml')
        self.config['mom_input_nml_tmpl'] = os.path.join(DATA, 'mom_input.nml.tmpl')
        self.config['mom_input_nml'] = os.path.join(DATA, 'mom_input.nml')
        self.config['bkg_dir'] = os.path.join(DATA, 'bkg')
        self.config['INPUT'] = os.path.join(DATA, 'INPUT')
        self.config['ens_dir'] = os.path.join(DATA, 'ens')

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
        RUN = self.runtime_config.RUN
        gcyc = self.runtime_config.gcyc

        ufsda.stage.soca_fix(self.recen_config)

        ################################################################################
        # prepare input.nml
        FileHandler({'copy': [[self.config.mom_input_nml_src, self.config.mom_input_nml_tmpl]]}).sync()

        # swap date and stack size
        domain_stack_size = self.config.DOMAIN_STACK_SIZE
        ymdhms = [int(s) for s in self.config.window_begin.strftime('%Y,%m,%d,%H,%M,%S').split(',')]
        with open(self.config.mom_input_nml_tmpl, 'r') as nml_file:
            nml = f90nml.read(nml_file)
            nml['ocean_solo_nml']['date_init'] = ymdhms
            nml['fms_nml']['domains_stack_size'] = int(domain_stack_size)
            ufsda.disk_utils.removefile(self.config.mom_input_nml)
            nml.write(self.config.mom_input_nml)

        FileHandler({'mkdir': [self.config.bkg_dir]}).sync()
        bkg_utils.gen_bkg_list(bkg_path=self.config.COM_OCEAN_HISTORY_PREV,
                               out_path=self.config.bkg_dir,
                               window_begin=self.config.window_begin,
                               yaml_name=self.config.BKG_LIST)

        ################################################################################
        # Copy initial condition

        bkg_utils.stage_ic(self.config.bkg_dir, self.runtime_config.DATA, RUN, gcyc)

        ################################################################################
        # stage ensemble members
        logger.info("---------------- Stage ensemble members")
        FileHandler({'mkdir': [self.config.ens_dir]}).sync()
        nmem_ens = self.config.NMEM_ENS
        gPDYstr = self.runtime_config.gPDY.strftime("%Y%m%d")
        ens_member_list = []
        for mem in range(1, nmem_ens+1):
            for domain in ['ocean', 'ice']:
                mem_dir = os.path.join(self.config.ROTDIR,
                                       f'enkf{RUN}.{gPDYstr}',
                                       f'{gcyc}',
                                       f'mem{str(mem).zfill(3)}',
                                       'model_data',
                                       domain,
                                       'history')
                mem_dir_real = os.path.realpath(mem_dir)
                f009 = f'enkf{RUN}.{domain}.t{gcyc}z.inst.f009.nc'

                fname_in = os.path.abspath(os.path.join(mem_dir_real, f009))
                fname_out = os.path.realpath(os.path.join(self.config.ens_dir,
                                             domain+"."+str(mem)+".nc"))
                ens_member_list.append([fname_in, fname_out])

        FileHandler({'copy': ens_member_list}).sync()

        ################################################################################
        # generate the YAML file for recenterer

        logger.info(f"---------------- generate soca_ensrecenter.yaml")

        recen_yaml = parse_j2yaml(self.config.recen_yaml_template, self.recen_config)
        recen_yaml.save(self.config.recen_yaml_file)

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

        chdir(self.runtime_config.DATA)

        exec_cmd_gridgen = Executable(self.config.APRUN_OCNANALECEN)
        exec_name_gridgen = os.path.join(self.config.JEDI_BIN, 'soca_gridgen.x')
        exec_cmd_gridgen.add_default_arg(exec_name_gridgen)
        exec_cmd_gridgen.add_default_arg(self.config.gridgen_yaml)

        try:
            logger.debug(f"Executing {exec_cmd_gridgen}")
            exec_cmd_gridgen()
        except OSError:
            raise OSError(f"Failed to execute {exec_cmd_gridgen}")
        except Exception:
            raise WorkflowException(f"An error occured during execution of {exec_cmd_gridgen}")
        pass

        exec_cmd_recen = Executable(self.config.APRUN_OCNANALECEN)
        exec_name_recen = os.path.join(self.config.JEDI_BIN, 'gdas_ens_handler.x')
        exec_cmd_recen.add_default_arg(exec_name_recen)
        exec_cmd_recen.add_default_arg(os.path.basename(self.config.recen_yaml_file))

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

        RUN = self.runtime_config.RUN
        cyc = self.runtime_config.cyc
        incr_file = f'enkf{RUN}.t{cyc}z.ocninc.nc'
        nmem_ens = self.config.NMEM_ENS
        PDYstr = self.runtime_config.PDY.strftime("%Y%m%d")
        mem_dir_list = []
        copy_list = []

        for mem in range(1, nmem_ens+1):
            mem_dir = os.path.join(self.config.ROTDIR,
                                   f'enkf{RUN}.{PDYstr}',
                                   f'{cyc}',
                                   f'mem{str(mem).zfill(3)}',
                                   'analysis',
                                   'ocean',
                                   'restart')
            mem_dir_real = os.path.realpath(mem_dir)
            mem_dir_list.append(mem_dir_real)

            copy_list.append([f'ocn.pert.steric.{str(mem)}.nc',
                              os.path.join(mem_dir_real, incr_file)])

        FileHandler({'mkdir': mem_dir_list}).sync()
        FileHandler({'copy': copy_list}).sync()
