import datetime
import os
from solo.yaml_file import YAMLFile
from solo.template import TemplateConstants, Template

def genYAML(input_config_dict, template=None, output=None):
    """
    genYAML(input_config_dict, template=None, output=None)

    generate YAML file based on inpput configuration dictionary,
    environment variables, and optional template.

    input_config_dict - input configuration dictionary
    template          - path to template YAML file
    output            - path to output YAML file
    """
    # call the parse_config function to create the final dict
    config_out = parse_config(input_config_dict, template=template)
    if not output:
        output = os.path.join(os.getcwd(), 'genYAML_out.yaml')
    config_out.save(output)

def parse_config(input_config_dict, template=None, clean=True):
    """
    parse_config(input_config_dict, template=None, clean=True)

    returns a config dict based on input_config_dict, environment vars,
    and matches an optional template.

    input_config_dict - input configuration dictionary
    template          - path to template YAML file
    clean             - if True, and template not None, removes top level dict keys not in template
    """
    if template:
        # open template YAML twice
        # once for processing, once for cleaning later
        config_temp = YAMLFile(template)
        config_out = YAMLFile(template)
    else:
        config_out = YAMLFile(data={})
    # add input_config_dict vars to config for substitutions
    config_out.update(input_config_dict)
    # do a first round of includes first
    config_out = include_yaml(config_out)
    # pull common key values out to top layer
    config_out = pop_out_common(config_out)
    # TODO create some vars in config based on other vars if they exist
    # now recursively update config dict
    config_out = update_config(config_out)
    # clean up if specified
    if clean and template is not None:
        config_out = clean_yaml(config_out, config_temp)

    return config_out

def pop_out_common(config_out):
    # to help with substitution, put all keys in the common key
    # in the top level of the config instead
    common = config_out['common']
    for key, value in common.items():
        config_out[key] = value
    del config_out['common']
    return config_out

def clean_yaml(config_out, config_template):
    # if there are nested keys, move the nest up one
    config_out = remove_nesting(config_out)
    # remove top level keys in config_out if they do not appear in config_template
    keys_to_del = []
    for key, value in config_out.items():
        if key not in config_template:
            keys_to_del.append(key)
    for key in keys_to_del:
        del config_out[key]
    return config_out

def remove_nesting(config):
    # if key is nested, pull it up one level in the dict
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, dict):
                if key in value.keys():
                    config[key] = value[key]
                remove_nesting(value)
    return config

def include_yaml(config):
    # look for the include yaml string and if it exists
    # 'include' that YAML in the config dictionary
    incstr = '$<<'
    for rootkey, rootval in config.items():
        if type(rootval) is list:
            # handle lists in the dictionary
            newlist = []
            for item in rootval:
                if incstr in item:
                    incpath = item.replace(incstr, '').strip()
                    newconfig = YAMLFile(incpath)
                    newlist.append(newconfig)
                else:
                    newlist.append(item)  # keeps something in the list if it is not an include
            config[rootkey] = newlist
        else:
            # handle single includes
            if incstr in rootval:
                incpath = rootval.replace(incstr, '').strip()
                newconfig = YAMLFile(incpath)
                config[rootkey] = newconfig
    return config

def replace_vars(config):
    # use SOLO to replace variables in the configuration dictionary
    # as appropriate with either other dictionary key/value pairs
    # or environment variables
    config = Template.substitute_structure_from_environment(config)
    config = Template.substitute_with_dependencies(config, config, TemplateConstants.DOLLAR_PARENTHESES)
    config = Template.substitute_structure(config, TemplateConstants.DOUBLE_CURLY_BRACES, config.get)
    return config

def iter_config(config, subconfig):
    # iterate through the config and do substitution and include YAMLs
    subconfig = Template.substitute_structure_from_environment(subconfig)
    subconfig = Template.substitute_structure(subconfig, TemplateConstants.DOUBLE_CURLY_BRACES, config.get)
    subconfig = Template.substitute_structure(subconfig, TemplateConstants.DOLLAR_PARENTHESES, config.get)
    subconfig = include_yaml(subconfig)
    subconfig = replace_vars(subconfig)
    if isinstance(subconfig, dict):
        for key, value in subconfig.items():
            if isinstance(value, dict):
                value = iter_config(config, value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        item = iter_config(config, item)
    return subconfig


def update_config(config):
    # drill through configuration and add includes and replace vars
    config = replace_vars(config)
    config = include_yaml(config)
    config = replace_vars(config)
    for key, value in config.items():
        if isinstance(value, dict):
            value = iter_config(config, value)
    return config


