import r2d2
from solo.configuration import Configuration
from solo.date import date_sequence, Hour


def store(config):
    component = config.get('component', 'atm')
    times = date_sequence(config.start, config.end, config.step)
    obs_types = config.obs_types
    provider = config.provider
    experiment = config.experiment
    database = config.database
    type = config.type
    source_dir = config.source_dir
    source_file_fmt = config.source_file_fmt
    step = config.step
    dump = config.get('dump', 'gdas')

    for time in times:
        year = Hour(time).format('%Y')
        month = Hour(time).format('%m')
        day = Hour(time).format('%d')
        hour = Hour(time).format('%H')
        for obs_type in obs_types:
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
