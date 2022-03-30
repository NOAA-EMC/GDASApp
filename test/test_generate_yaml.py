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
        'common': f'$<< {parm_dir}/atm/common/paths.yaml',
        'BKG_DIR': '/this/is/not/a/real/path',
        'OBS_LIST': f'{parm_dir}/atm/obs/lists/gdas_prototype.yaml',
    }
    # now call the function to do all of the heavy lifting
    ufsda.yamltools.genYAML(config_dict, template=template, output=output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parm", type=str,
                        help="Path to parm/ directory", required=True)
    args = parser.parse_args()
    test_yaml_gen_yaml(args.parm)
