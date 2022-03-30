# test to see if YAML cocnatenation/generation tools are working
import argparse
import os
import ufsda
import yaml


def test_yaml_gen_yaml(parm_dir):
    # test generating YAML from config dict, env, and template
    output_file = os.path.join(os.getcwd(), 'testoutput', 'test_yaml_gen.yaml')
    template = os.path.join(parm_dir, 'atm/variational/3dvar_dripcg.yaml')
    config_dict = {
        'paths': f'$<< {parm_dir}/atm/common/paths.yaml',
        'atm_case': f'$<< {parm_dir}/atm/common/c384.yaml',
        'BKG_DIR': '/this/is/not/a/real/path',
        'OBS_LIST': f'{parm_dir}/atm/obs/lists/gdas_prototype.yaml',
        'fv3jedi_fix_dir': 'Data/fv3files',
        'fv3jedi_fieldset_dir': 'Data/fieldsets',
        'ANL_DIR': '/fake/path/to/analysis',
        'fv3jedi_staticb_dir': '/fake/path/to/berror',
        'BIAS_DIR': '/fake/path/to/biascoeff',
        'CRTM_COEFF_DIR': '/fake/path/to/crtm',
        'BIAS_PREFIX': 'gdas.t18z',
        'BIAS_DATE': '${gPDY}${gcyc}',
        'DIAG_DIR': '/fake/output/path',
        'OBS_DIR': '/fake/path/to/obs',
        'OBS_PREFIX': 'gdas.t00z',
        'OBS_DATE': '${PDY}${cyc}',
    }
    # now call the function to do all of the heavy lifting
    ufsda.yamltools.genYAML(config_dict, template=template, output=output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parm", type=str,
                        help="Path to parm/ directory", required=True)
    args = parser.parse_args()
    test_yaml_gen_yaml(args.parm)
