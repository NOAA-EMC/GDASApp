import numpy as np
import bufr
from pyioda.ioda.Engines.Bufr import Encoder


def mask_container(container, mask):
    new_container = bufr.DataContainer()
    for var_name in container.list():
        var = container.get(var_name)
        paths = container.get_paths(var_name)
        new_container.add(var_name, var[mask], paths)

    return new_container


def create_obs_group(input_path):
    """Create the ioda snow observations
    This method:
    - reads state of ground (sogr) and snow depth (snod)
    - applys sogr conditions to the missing snod values
    - removes the filled/missing snow values and creates the masked container
    - encoders the new container.

    Parameters
    ----------
    input_path
        The input bufr file
    """

    YAML_PATH = "./obs/bufr_sfcsno_mapping.yaml"
    container = bufr.Parser(input_path, YAML_PATH).parse()

    sogr = container.get('variables/groundState')
    snod = container.get('variables/totalSnowDepth')
    snod[(sogr <= 11.0) & snod.mask] = 0.0
    snod[(sogr == 15.0) & snod.mask] = 0.0
    container.replace('variables/totalSnowDepth', snod)

    masked_container = mask_container(container, (~snod.mask))

    data = next(iter(Encoder(YAML_PATH).encode(masked_container).values()))

    return data
