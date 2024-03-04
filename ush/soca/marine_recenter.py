#!/usr/bin/env python3

from datetime import datetime, timedelta
import f90nml
from logging import getLogger
import os
from soca import bkg_utils
from typing import Dict
import ufsda
from ufsda.stage import soca_fix
from wxflow import (chdir,
                    Executable,
                    FileHandler,
                    logit,
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
        PDY = self.runtime_config['PDY']
        cyc = self.runtime_config['cyc']
        cdate = PDY + timedelta(hours=cyc)
        gdate = cdate - timedelta(hours=6)
        self.runtime_config['gcyc'] = gdate.strftime("%H")

        gdas_home = os.path.join(config['HOMEgfs'], 'sorc', 'gdas.cd')
        half_assim_freq = timedelta(hours=int(config['assim_freq'])/2)
        window_begin = cdate - half_assim_freq
        window_begin_iso = window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
        window_middle_iso = cdate.strftime('%Y-%m-%dT%H:%M:%SZ')

        self.window_config = {'window_begin': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
                              'ATM_WINDOW_BEGIN': window_begin_iso,
                              'ATM_WINDOW_MIDDLE': window_middle_iso,
                              'ATM_WINDOW_LENGTH': f"PT{config['assim_freq']}H"}

        stage_cfg = YAMLFile(path=os.path.join(gdas_home, 'parm', 'templates', 'recen.yaml'))
        stage_cfg = Template.substitute_structure(stage_cfg, TemplateConstants.DOUBLE_CURLY_BRACES, self.window_config.get)
        stage_cfg = Template.substitute_structure(stage_cfg, TemplateConstants.DOLLAR_PARENTHESES, self.window_config.get)
        self.stage_cfg = stage_cfg

        self.config['window_begin'] = window_begin
        self.config['mom_input_nml_src'] = os.path.join(gdas_home, 'parm', 'soca', 'fms', 'input.nml')
        self.config['mom_input_nml_tmpl'] = os.path.join(stage_cfg['stage_dir'], 'mom_input.nml.tmpl')
        self.config['mom_input_nml'] = os.path.join(stage_cfg['stage_dir'], 'mom_input.nml')
        self.config['bkg_dir'] = os.path.join(self.runtime_config.DATA, 'INPUT')
        self.config['ens_dir'] = os.path.join(self.runtime_config.DATA, 'ens')

        self.config['gridgen_yaml'] = os.path.join(gdas_home, 'parm', 'soca', 'gridgen', 'gridgen.yaml')
        self.config['BKG_LIST'] = 'bkg_list.yaml'

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

        ufsda.stage.soca_fix(self.stage_cfg)


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

        bkg_utils.stage_ic(self.config.bkg_dir, self.runtime_config.DATA, self.runtime_config.RUN, self.runtime_config.gcyc)

        ################################################################################
        # stage ensemble members
        logger.info("---------------- Stage ensemble members")
        FileHandler({'mkdir': [self.config.ens_dir]}).sync()
        nmem_ens = self.config.NMEM_ENS
        PDYstr = self.runtime_config.PDY.strftime("%Y%m%d")
        ens_member_list = []
        for mem in range(1, nmem_ens+1):
            for domain in ['ocean', 'ice']:
                # TODO(Guillaume): make use and define ensemble COM in the j-job
                ensdir = os.path.join(self.config.COM_OCEAN_HISTORY_PREV,
                                      '..', '..', '..', '..', '..',
                                      f'enkf{self.runtime_config.RUN}.{PDYstr}',
                                      f'{self.runtime_config.gcyc}',
                                      f'mem{str(mem).zfill(3)}',
                                      'model_data',
                                      domain,
                                      'history')
                ensdir_real = os.path.realpath(ensdir)
                f009 = f'enkfgdas.{domain}.t{self.runtime_config.gcyc}z.inst.f009.nc'

                fname_in = os.path.abspath(os.path.join(ensdir_real, f009))
                fname_out = os.path.realpath(os.path.join(self.config.ens_dir,
                                             domain+"."+str(mem)+".nc"))
                ens_member_list.append([fname_in, fname_out])
        FileHandler({'copy': ens_member_list}).sync()




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

        exec_cmd = Executable(self.config.APRUN_OCNANALECEN)
        exec_name = os.path.join(self.config.JEDI_BIN, 'soca_gridgen.x')
        exec_cmd.add_default_arg(exec_name)
        exec_cmd.add_default_arg(self.config.gridgen_yaml)

        try:
            logger.debug(f"Executing {exec_cmd}")
            exec_cmd()
        except OSError:
            raise OSError(f"Failed to execute {exec_cmd}")
        except Exception:
            raise WorkflowException(f"An error occured during execution of {exec_cmd}")

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
