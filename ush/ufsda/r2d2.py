import r2d2
from solo.configuration import Configuration
from solo.date import date_sequence, Hour

fv3files = ['fv_core.res', 'fv_srf_wnd.res', 'fv_tracer.res', 'phy_data', 'sfc_data']


def store(config):
    times = date_sequence(config.start, config.end, config.step)
    obs_types = config.get('obs_types', ['dummy'])
    provider = config.get('provider', None)
    experiment = config.experiment
    database = config.database
    type = config.type
    file_type = config.get('file_type', None)
    source_dir = config.source_dir
    source_file_fmt = config.source_file_fmt
    step = config.get('step', 'PT6H')
    fcst_steps = config.get('forecast_steps', ['PT6H'])
    dump = config.get('dump', 'gdas')
    resolution = config.get('resolution', 'c768')
    model = config.get('model', 'gfs')
    user_date_format = config.get('user_date_format', '%Y%m%d.%H%M%S')
    fc_date_rendering = config.get('fc_date_rendering', 'analysis')
    tiles = config.get('tiles', [1, 2, 3, 4, 5, 6])
    file_type_list = config.get('file_type_list', fv3files)

    for time in times:
        year = Hour(time).format('%Y')
        month = Hour(time).format('%m')
        day = Hour(time).format('%d')
        hour = Hour(time).format('%H')
        if type in ['bc', 'ob']:
            for obs_type in obs_types:
                if type == 'bc':
                    r2d2.store(
                        provider=provider,
                        type=type,
                        file_type=file_type,
                        experiment=experiment,
                        database=database,
                        date=time,
                        obs_type=obs_type,
                        source_file=eval(f"f'{source_file_fmt}'"),
                        ignore_missing=True,
                    )
                else:
                    r2d2.store(
                        provider=provider,
                        type=type,
                        experiment=experiment,
                        database=database,
                        date=time,
                        obs_type=obs_type,
                        time_window=step,
                        source_file=eval(f"f'{source_file_fmt}'"),
                        ignore_missing=True,
                    )
        elif type == 'fc':
            if model == 'gfs_metadata':
                r2d2.store(
                    type=type,
                    model=model,
                    experiment=experiment,
                    date=time,
                    step=fcst_steps,
                    resolution=resolution,
                    user_date_format=user_date_format,
                    fc_date_rendering=fc_date_rendering,
                    database=database,
                    file_type=['coupler.res', 'fv_core.res.nc'],
                    source_file=eval(f"f'{source_file_fmt}'"),
                )
            else:
                r2d2.store(
                    type=type,
                    model=model,
                    experiment=experiment,
                    date=time,
                    step=fcst_steps,
                    resolution=resolution,
                    user_date_format=user_date_format,
                    fc_date_rendering=fc_date_rendering,
                    database=database,
                    file_type=file_type_list,
                    tile=tiles,
                    source_file=eval(f"f'{source_file_fmt}'"),
                )
