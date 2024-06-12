#!/usr/bin/env python3


# --------------------------------------------------------------------------------------------------


import jinja2 as j2
import os
import yaml


# --------------------------------------------------------------------------------------------------


def generate_bundle():

    # Get the path of this file
    root = os.path.dirname(os.path.realpath(__file__))

    # Open the gdas_bundle.yaml file
    with open(os.path.join(root, 'gdas_jedi_bundle.yaml'), 'r') as f:
        bundles = yaml.safe_load(f)

    # Loop over bundles and make sure all items have pre_include and post_include keys
    bundle_dicts = bundles['jedi_packages']
    for bundle_dict in bundle_dicts:
        if 'package_name' not in bundle_dict:
            bundle_dict['package_name'] = bundle_dict['project']

    # Open CMakeLists-JEDI.txt.j2
    with open(os.path.join(root, 'CMakeLists-JEDI.j2.txt'), 'r') as f:
        cmake_template = j2.Template(f.read())

    # Render the template with the data
    cmake_rendered = cmake_template.render(bundles)

    # Write rendered to CMakeLists.txt
    cmake_output_file = os.path.join(root, 'CMakeLists.txt')
    if os.path.exists(cmake_output_file):
        os.remove(cmake_output_file)
    with open(cmake_output_file, 'w') as f:
        f.write(cmake_rendered)


# --------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    generate_bundle()


# --------------------------------------------------------------------------------------------------
