import numpy as np
import bufr
from pyioda.ioda.Engines.Bufr import Encoder


def mask_container(container, mask):
    new_container = bufr.DataContainer()
    for var_name in container.list():
        print(f" ... variable name: {var_name} ...")
        var = container.get(var_name)
        paths = container.get_paths(var_name)
        new_container.add(var_name, var[mask], paths)

    return new_container

def create_obs_group(input_path):
    YAML_PATH = "./obs/bufr_sfcsno_mapping.yaml"
    container = bufr.Parser(input_path, YAML_PATH).parse()

    sogr = container.get('variables/groundState')
    snod = container.get('variables/totalSnowDepth')
    snod[(sogr < 10.0) | (sogr == 11.0) | (sogr == 15.0)] = 0.0
    container.replace('variables/totalSnowDepth', snod)

    print(f" ... Remove filled/missing snow values ...")
    masked_container = mask_container(container, (~snod.mask))

    encoder = Encoder(YAML_PATH)
    data = next(iter(encoder.encode(masked_container).values()))

    return data
