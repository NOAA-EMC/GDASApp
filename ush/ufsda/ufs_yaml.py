import datetime
import os
from solo.yaml_file import YAMLFile
from solo.template import TemplateConstants, Template


def gen_yaml(outyaml, templateyaml):
    """
    gen_yaml(outyaml, templateyaml)
        driver function to produce a full
        YAML file based on variables in
        `templateyaml` and the runtime
        environment and write to `outyaml`
    """
    # call parse_config to get vars
    config_out = parse_config(templateyaml=templateyaml)

    # write to outyaml
    config_out.save(outyaml)
    print(f'Wrote to {outyaml}')


def parse_config(templateyaml=None, clean=True):
    """
    parse_config(templateyaml=None)
        returns a config dict based on
        some environment variables and
        an optional template output YAML
    """
    if templateyaml:
        # open template YAML file twice
        # once for output, once for filtering
        print(f'Using {templateyaml} as template')
        config_temp = YAMLFile(templateyaml)
        config_out = YAMLFile(templateyaml)
    else:
        config_out = YAMLFile(data={})
    # grab experiment specific variables and add them to config
    exp_dict = get_exp_vars()
    config_out.update(exp_dict)
    # grab cycle specific time variables and add them to config
    cycle_dict = get_cycle_vars()
    config_out.update(cycle_dict)
    # define bundle based on env var
    config_out['bundle'] = os.path.join(os.environ['HOMEgfs'], 'sorc', 'ufs_da.fd', 'UFS-DA', 'src')
    # going to now nest multiple times to do includes and replace
    config_out = update_config(config_out)
    if clean:
        # clean up to match original template
        config_out = clean_yaml(config_out, config_temp)

    return config_out


def include_yaml_list(item):
    # return a dict if there is just an include str
    incstr = '$<<'
    if incstr in item:
        incpath = item.replace(incstr, '').strip()
        newconfig = YAMLFile(incpath)
        return newconfig
    else:
        return item


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
                    newlist.append(item) # keeps something in the list if it is not an include
            config[rootkey] = newlist
        else:
            # handle single includes
            if incstr in rootval:
                incpath = rootval.replace(incstr, '').strip()
                newconfig = YAMLFile(incpath)
                config[rootkey] = newconfig
    return config


def get_cycle_vars():
    cycle_dict = {}
    cdate = datetime.datetime.strptime(os.environ['CDATE'], '%Y%m%d%H')
    gdate = datetime.datetime.strptime(os.environ['GDATE'], '%Y%m%d%H')
    assim_freq = os.environ['assim_freq']
    cycle_dict['window_length'] = f'PT{assim_freq}H'
    win_begin = cdate - datetime.timedelta(hours=int(assim_freq)/2)
    cycle_dict['window_begin'] = win_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
    cycle_dict['background_time'] = gdate.strftime('%Y-%m-%dT%H:%M:%SZ')
    cycle_dict['fv3_bkg_time'] = cdate.strftime('%Y%m%d.%H%M%S')
    cycle_dict['fv3_bkg_datetime'] = cdate.strftime('%Y-%m-%dT%H:%M:%SZ')
    cycle_dict['current_cycle'] = cdate.strftime('%Y%m%d%H')
    cycle_dict['background_dir'] = os.environ['COMIN_GES']
    cycle_dict['staticb_dir'] = os.environ['STATICB_DIR']
    cycle_dict['COMOUT'] = os.environ['COMOUT']
    return cycle_dict


def get_exp_vars():
    # variables computed from shell variables but not time dependent
    exp_dict = {}
    npx_anl = str(int(os.getenv('CASE_ENKF', os.environ['CASE'])[1:]) + 1)
    npx = str(int(os.environ['CASE'][1:]) + 1)
    exp_dict['npx_anl'] = npx_anl
    exp_dict['npy_anl'] = npx_anl
    exp_dict['npx_ges'] = npx
    exp_dict['npy_ges'] = npx
    exp_dict['npz'] = str(int(os.environ['LEVS'])-1)
    exp_dict['experiment'] = os.getenv('PSLOT', 'oper') + '_' + os.getenv('CDUMP', 'gdas')
    exp_dict['jedi_build'] = os.path.join(os.environ['HOMEgfs'], 'sorc', 'ufs_da.fd', 'UFS-DA', 'build')
    exp_dict['experiment_dir'] = 'Data/obs'
    return exp_dict


def replace_vars(config):
    # use SOLO to replace variables in the configuration dictionary
    # as appropriate with either other dictionary key/value pairs
    # or environment variables
    config = Template.substitute_structure_from_environment(config)
    config = Template.substitute_with_dependencies(config, config, TemplateConstants.DOLLAR_PARENTHESES)
    config = Template.substitute_structure(config, TemplateConstants.DOUBLE_CURLY_BRACES, config.get)
    return config


def iter_config(config, subconfig):
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

def remove_nesting(config):
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, dict):
                if key in value.keys():
                    config[key] = value[key]
                remove_nesting(value)
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
