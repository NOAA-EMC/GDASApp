import yaml
import sys

def parse_yaml(file_path):
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    return data

if __name__ == "__main__":
    yaml_file = sys.argv[1]
    data = parse_yaml(yaml_file)
    print(f"{data['idate']")
    for key, value in data.items():
        print(f"{key}={value}")
