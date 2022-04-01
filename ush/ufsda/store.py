from r2d2 import store
from solo.configuration import Configuration
from solo.date import date_sequence, Hour


def obs(config):
    component = config.get('component', 'atm')
    times = date_sequence(config.start, config.end, config.step)
    obs_types = config.obs_types
    provider = config.provider
    experiment = config.experiment
    database = config.database
    type = config.type
    source_dir = config.source_dir
    step = config.step
    dump = config.get('dump', 'gdas')

    for time in times:
        year = Hour(time).format('%Y')
        month = Hour(time).format('%m')
        day = Hour(time).format('%d')
        hour = Hour(time).format('%H')
        if component == 'atm':
            cdate = f"{year}{month}{day}{hour}"
            datadir = f"{dump}.{year}{month}{day}/{hour}/atmos/"
        elif component == 'soca':
            cdate = f"{year}{month}{day}"
            datadir = ""
        else:
            raise ValueError(f"{component} not supported yet")
        store(
            provider=provider,
            type=type,
            experiment=experiment,
            database=database,
            date=time,
            obs_type=obs_type,
            time_window=step,
            source_file=f'{source_dir}/{datadir}{obs_type}_{cdate}.nc4',
            ignore_missing=True,
        )
