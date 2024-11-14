import json
import yaml
import argparse

def convert_json_to_yaml(input_file, output_file):
    # Load the JSON data from the input file
    with open(input_file, 'r') as json_file:
        json_data = json.load(json_file)

    # Convert and save as YAML in the output file
    with open(output_file, 'w') as yaml_file:
        yaml.dump(json_data, yaml_file, default_flow_style=False)

if __name__ == '__main__':
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Convert JSON to YAML.')
    parser.add_argument('input_file', help='Path to the input JSON file')
    parser.add_argument('output_file', help='Path to the output YAML file')

    args = parser.parse_args()

    # Perform the conversion
    convert_json_to_yaml(args.input_file, args.output_file)

