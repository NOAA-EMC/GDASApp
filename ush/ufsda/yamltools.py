import os

def genYAML(input_config_dict, template=None, output=None):
    """
    genYAML(input_config_dict, template=None, output=None)

    generate YAML file based on inpput configuration dictionary,
    environment variables, and optional template.

    input_config_dict - input configuration dictionary
    template          - path to template YAML file
    output            - path to output YAML file
    """
