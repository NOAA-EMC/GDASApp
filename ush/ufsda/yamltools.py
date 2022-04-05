import datetime
import os
import re
from solo.yaml_file import YAMLFile
from solo.template import TemplateConstants, Template
from ufsda import isTrue


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
    # compute common resolution variables
    if config_out.get('atm', True):
        config_out = atmanl_case(config_out)
    # do a first round of includes first
    config_out = include_yaml(config_out)
    # pull common key values out to top layer
    config_out = pop_out_common(config_out)
    # TODO create some vars in config based on other vars if they exist
    # calculate time/cycle variables
    config_out = calc_time_vars(config_out)
    # now recursively update config dict
    config_out = update_config(config_out)
    # clean up if specified
    if clean and template is not None:
        config_out = clean_yaml(config_out, config_temp)

    return config_out


def atmanl_case(config):
    # compute atm analysis case/res variables based on environment and/or config
    case = int(os.environ.get('CASE', 'C768')[1:])
    case_enkf = int(os.environ.get('CASE_ENKF', 'C384')[1:])
    levs = int(os.environ.get('LEVS', '128'))
    dohybvar = isTrue(os.environ.get('DOHYBVAR', 'NO'))
    # get background geometry
    ntiles = 6 # global, fix later to be more generic
    layout = [
        os.environ.get('layout_x', '$(layout_x)'),
        os.environ.get('layout_y', '$(layout_y)'),
    ]
    io_layout = [1, 1] # force to be one file for forseeable future
    config['GEOM_BKG'] = fv3_geom_dict(case, levs, ntiles, layout, io_layout)
    # get analysis geometry depending on dohybvar
    if dohybvar:
        config['GEOM_ANL'] = fv3_geom_dict(case_enkf, levs, ntiles, layout, io_layout)
    else:
        config['GEOM_ANL'] = fv3_geom_dict(case, levs, ntiles, layout, io_layout)
    return config


def fv3_geom_dict(case, levs, ntiles, layout, io_layout):
    # returns a dictionary matching FV3-JEDI global geometry entries
    outdict = {
        'fms initialization': {
            'namelist filename': '$(fv3jedi_fix_dir)/fmsmpp.nml',
            'field table filename': '$(fv3jedi_fix_dir)/field_table',
        },
        'akbk': '$(fv3jedi_fix_dir)/akbk.nc4',
        'layout': layout,
        'io_layout': io_layout,
        'npx': str(case+1),
        'npy': str(case+1),
        'npz': str(levs-1),
        'ntiles': str(ntiles),
        'fieldsets': [
            {'fieldset': '$(fv3jedi_fieldset_dir)/dynamics.yaml'},
            {'fieldset': '$(fv3jedi_fieldset_dir)/ufo.yaml'},
        ]
    }
    return outdict


def calc_time_vars(config):
    # compute time variables in different formats
    # based on existing variables
    if all(key in os.environ for key in ('PDY', 'cyc')):
        valid_time_obj = datetime.datetime.strptime(f"{os.environ['PDY']}{os.environ['cyc']}",
                                                    "%Y%m%d%H")
    elif 'valid_time' in config.keys():
        valid_time_obj = datetime.datetime.strptime(config['valid_time'],
                                                    "%Y-%m-%dT%H:%M:%SZ")
    else:
        raise KeyError("Neither $(valid_time) nor ${PDY}${cyc} defined")
    config['YYYYMMDDpHHMMSS'] = valid_time_obj.strftime('%Y%m%d.%H%M%S')
    # for now bkg_time == valid_time, will change for fgat
    bkg_time_obj = valid_time_obj
    config['BKG_YYYYMMDDpHHMMSS'] = bkg_time_obj.strftime('%Y%m%d.%H%M%S')
    config['BKG_ISOTIME'] = bkg_time_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
    if 'assim_freq' in os.environ:
        config['ATM_WINDOW_LENGTH'] = f"PT{os.environ['assim_freq']}H"
    elif 'atm_window_length' in config.keys():
        config['ATM_WINDOW_LENGTH'] = config['atm_window_length']
    else:
        raise KeyError("Neither $(atm_window_length) nor ${assim_freq} defined")
    # get atm window begin
    h = re.findall('PT(\\d+)H', config['ATM_WINDOW_LENGTH'])[0]
    win_begin = valid_time_obj - datetime.timedelta(hours=int(h)/2)
    config['ATM_WINDOW_BEGIN'] = win_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
    return config


def pop_out_common(config):
    # to help with substitution, put all keys in the common key
    # in the top level of the config instead
    for commonkey in ['paths', 'atm_case']:
        if commonkey in config.keys():
            common = config[commonkey]
            for key, value in common.items():
                config[key] = value
            del config[commonkey]
    return config


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
