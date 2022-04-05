import r2d2
from solo.configuration import Configuration
from solo.date import date_sequence, Hour

fv3files = ['fv_core.res', 'fv_srf_wnd.res', 'fv_tracer.res', 'phy_data', 'sfc_data']
possible_args = [
    'obs_types', 'provider', 'experiment', 'database', 'type', 'file_type',
    'resolution', 'model', 'user_date_format', 'fc_date_rendering', 'tile',
]


def store(config):
    kwargs = {}
    kwargs['ignore_missing'] = True
    for arg in config.keys():
        if arg in possible_args:
            kwargs[arg] = config[arg]
    times = date_sequence(config.start, config.end, config.step)
    dump = config.get('dump', 'gdas')
    source_dir = config['source_dir']
    source_file_fmt = config['source_file_fmt']

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
