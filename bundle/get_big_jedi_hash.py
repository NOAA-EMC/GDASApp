#!/usr/bin/env python3


# --------------------------------------------------------------------------------------------------


import hashlib
import os
import yaml


# --------------------------------------------------------------------------------------------------


def combine_hashes(hashes):
    # Concatenate all hashes in the list of hashes
    combined = ''
    for hash in hashes:
        combined += hash

    # Create sha1 hash for the long string
    combined_hash = hashlib.sha1(combined.encode()).hexdigest()

    return combined_hash


# --------------------------------------------------------------------------------------------------


def get_jedi_big_hash():

    # Get the path of this file
    root = os.path.dirname(os.path.realpath(__file__))

    # Set the sorc path
    base_path = os.path.join(root, '..')

    # Open the gdas_bundle.yaml file
    with open(os.path.join(root, 'gdas_jedi_bundle.yaml'), 'r') as f:
        bundles = yaml.safe_load(f)

    # Loop over the bundles and get the paths for packages coming from sorc
    sorc_package_paths = []
    jedi_packages = bundles['jedi_packages']
    for jedi_package in jedi_packages:
        if jedi_package['location'] == 'SOURCE':
            sorc_package_paths.append(os.path.join(root, jedi_package['path']))

    # For each sorc_package_paths get the git hash for that repo
    hashes = []
    for sorc_package_path in sorc_package_paths:
        os.chdir(sorc_package_path)
        hash = os.popen('git rev-parse HEAD').read().strip()
        # print(sorc_package_path, hash)
        hashes.append(hash)

    # Get a hash that represents the concatenation of hashes
    big_hash = combine_hashes(hashes)

    # Print the big hash (to be picked up by bash script usually)
    print(big_hash)

    # Done
    return


# --------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    get_jedi_big_hash()


# --------------------------------------------------------------------------------------------------
