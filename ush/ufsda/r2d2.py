import r2d2
from solo.configuration import Configuration
from solo.date import date_sequence, Hour

possible_args = [
    'provider', 'experiment', 'database', 'type', 'file_type',
    'resolution', 'model', 'user_date_format', 'fc_date_rendering', 'tile',
]


def store(config):
    inputs = {}
    inputs['ignore_missing'] = True
    for arg in config.keys():
        if arg in possible_args:
            inputs[arg] = config[arg]
    type = config.type
    times = date_sequence(config.start, config.end, config.step)
    dump = config.get('dump', 'gdas')
    source_dir = config['source_dir']
    source_file_fmt = config['source_file_fmt']
    obs_types = config.get('obs_types', None)

    for time in times:
        year = Hour(time).format('%Y')
        month = Hour(time).format('%m')
        day = Hour(time).format('%d')
        hour = Hour(time).format('%H')
        inputs['date'] = time
        if type in ['bc', 'ob']:
            if type == 'ob':
                inputs['time_window'] = config['step']
            for obs_type in obs_types:
                inputs['source_file'] = eval(f"f'{source_file_fmt}'"),
                inputs['obs_type'] = obs_type
                r2d2.store(**inputs)
        else:
            inputs['file_type'] = config.file_type_list
            inputs['step'] = config['forecast_steps']
            inputs['source_file'] = eval(f"f'{source_file_fmt}'"),
            r2d2.store(**inputs)


def fetch(config):
    inputs = {}
    inputs['ignore_missing'] = False
    for arg in config.keys():
        if arg in possible_args:
            inputs[arg] = config[arg]
    type = config.type
    times = date_sequence(config.start, config.end, config.step)
    dump = config.get('dump', 'gdas')
    obs_types = config.get('obs_types', None)
    target_dir = config['target_dir']
    target_file_fmt = config['target_file_fmt']
    for time in times:
        year = Hour(time).format('%Y')
        month = Hour(time).format('%m')
        day = Hour(time).format('%d')
        hour = Hour(time).format('%H')
        inputs['date'] = time
        if type in ['bc', 'ob']:
            if type == 'ob':
                inputs['time_window'] = config['step']
            for obs_type in obs_types:
                inputs['target_file'] = eval(f"f'{target_file_fmt}'"),
                inputs['obs_type'] = obs_type
                r2d2.fetch(**inputs)
        else:
            inputs['file_type'] = config.file_type_list
            inputs['step'] = config['forecast_steps']
            inputs['target_file'] = eval(f"f'{target_file_fmt}'"),
            r2d2.fetch(**inputs)
