# test to see if YAML cocnatenation/generation tools are working
import argparse
import os
import ufsda
import yaml


def test_yaml_gen_yaml(template_yaml, output_yaml):
    # test ufsda.gen_yaml after setting some env vars
    include_yaml = template_yaml.replace('.yaml', '_include.yaml')
    # this is needed for the unit test
    os.environ['TEST_INCLUDE_YAML'] = include_yaml
    # all of the below are currently required
    # this needs to be fixed later
    os.environ['CDATE'] = '2022032418'
    os.environ['GDATE'] = '2022032412'
    os.environ['assim_freq'] = '6'
    os.environ['COMIN_GES'] = './'
    os.environ['STATICB_DIR'] = './'
    os.environ['COMOUT'] = './'
    os.environ['CASE'] = 'C768'
    os.environ['CASE_ENKF'] = 'C384'
    os.environ['LEVS'] = '128'
    os.environ['PSLOT'] = 'GDASApp_tests'
    os.environ['CDUMP'] = 'gdas'
    os.environ['HOMEgfs'] = './'
    # generate the YAML file
    ufsda.gen_yaml(output_yaml, template_yaml)
    # read it back in
    myconfig = ufsda.parse_config(templateyaml=output_yaml, clean=True)
    print(myconfig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=str,
                        help="Input template YAML file", required=True)
    parser.add_argument("--output", type=str,
                        help="Output YAML file", required=True)
    args = parser.parse_args()
    test_yaml_gen_yaml(args.template, args.output)
