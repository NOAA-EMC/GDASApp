#!/usr/bin/env python3
import argparse
import logging
import os
import yaml


def gen_eva_obs_yaml(


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputyaml', type=str, help='Input JEDI YAML Configuration', required=True)
    parser.add_argument('-o', '--outputyaml', type=str, help='Output EVA YAML Configuration', required=True)
    args = parser.parse_args()
    gen_eva_obs_yaml(args.inputyaml, args.outputyaml)
