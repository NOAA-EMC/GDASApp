import re
import argparse
from datetime import datetime, timedelta

def read_idate_from_yaml(file_path):
    idate_value = None
    with open(file_path, 'r') as file:
        for line in file:
            match = re.search(r'^\s*idate:\s*(.*)', line)

            if match:
                idate_value = match.group(1).strip()
                break
    return idate_value

def format_dates(idate_str):
    date_obj = datetime.strptime(idate_str, '%Y%m%d%H')
    half_cycle = date_obj.strftime('%Y%m%d%H%M')
    new_date_obj = date_obj + timedelta(hours=6)
    full_cycle = new_date_obj.strftime('%Y%m%d%H%M')

    return half_cycle, full_cycle

def main():
    parser = argparse.ArgumentParser(description="Extract and format idate.")
    parser.add_argument('yaml_file', help="Path to exp.yaml file")
    args = parser.parse_args()

    idate_value = read_idate_from_yaml(args.yaml_file)
    half_cycle, full_cycle = format_dates(idate_value)
    print(f"{half_cycle},{full_cycle}")

if __name__ == "__main__":
    main()
