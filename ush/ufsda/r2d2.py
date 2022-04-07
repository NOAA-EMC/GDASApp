import r2d2
from solo.configuration import Configuration
from solo.date import date_sequence, Hour

possible_args = [
    'provider', 'experiment', 'database', 'type', 'file_type',
    'resolution', 'model', 'user_date_format', 'fc_date_rendering', 'tile',
]


def store(config):
    kwargs = {}
    kwargs['ignore_missing'] = True
    for arg in config.keys():
        if arg in possible_args:
            kwargs[arg] = config[arg]
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
        kwargs['date'] = time
        if type in ['bc', 'ob']:
            if type == 'ob':
                kwargs['time_window'] = config['step']
            for obs_type in obs_types:
                kwargs['source_file'] = eval(f"f'{source_file_fmt}'"),
                kwargs['obs_type'] = obs_type
                r2d2.store(**kwargs)
        else:
            kwargs['file_type'] = config.file_type_list
            kwargs['step'] = config['forecast_steps']
            kwargs['source_file'] = eval(f"f'{source_file_fmt}'"),
            r2d2.store(**kwargs)


def fetch(config):
    kwargs = {}
    kwargs['ignore_missing'] = False
    for arg in config.keys():
        if arg in possible_args:
            kwargs[arg] = config[arg]
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
        kwargs['date'] = time
        if type in ['bc', 'ob']:
            if type == 'ob':
                kwargs['time_window'] = config['step']
            for obs_type in obs_types:
                kwargs['target_file'] = eval(f"f'{target_file_fmt}'"),
                kwargs['obs_type'] = obs_type
                r2d2.fetch(**kwargs)
        else:
            kwargs['file_type'] = config.file_type_list
            kwargs['step'] = config['forecast_steps']
            kwargs['target_file'] = eval(f"f'{target_file_fmt}'"),
            r2d2.fetch(**kwargs)
