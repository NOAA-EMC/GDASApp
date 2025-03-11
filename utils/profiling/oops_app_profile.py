import argparse
import yaml
import matplotlib.pyplot as plt
import re

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Process profiling data from a YAML configuration file.')
parser.add_argument('config', type=str, help='Path to the YAML configuration file')
args = parser.parse_args()

# Load the YAML configuration file
with open(args.config, 'r') as yaml_file:
    config = yaml.safe_load(yaml_file)

# Extract the file path from the configuration
file_path = config['oops log']
methods = config['methods']

# Define a regex to extract parallel timing statistics
pattern = re.compile(r"OOPS_STATS\s+(.+?)\s+:\s+(\d+\.\d+)")

# Read and parse the file
runtimes = {}
in_parallel_section = False
with open(file_path, "r") as file:
    for line in file:
        if "---------------------------------- Parallel Timing Statistics" in line:
            if in_parallel_section:
                break  # Stop parsing at the end of the section
            else:
                in_parallel_section = True
                continue

        if in_parallel_section and "OOPS_STATS" in line:
            match = pattern.search(line)
            if match:
                key, runtime = match.groups()
                runtimes[key.strip()] = float(runtime) / 1000  # Convert ms to seconds

# Ensure there is data to plot
if runtimes:
    # Sort by runtime in descending order
    sorted_runtimes = sorted(runtimes.items(), key=lambda item: item[1], reverse=True)

    # Calculate cumulative runtime and determine the cutoff for the top 90%
    total_runtime = sum(runtime for _, runtime in sorted_runtimes)
    cumulative_runtime = 0
    top_runtimes = []
    other_runtime = 0
    # Convert sorted_runtimes to a dictionary
    sorted_runtimes_dict = {key: runtime for key, runtime in sorted_runtimes}

    # print the sorted_runtimes_dict one key/value pair per line
    for key, value in sorted_runtimes_dict.items():
        print(f"{key}: {value}")

    total_runtime_value = sorted_runtimes_dict['util::Timers::Total']

    for key, runtime in sorted_runtimes:
        if key in methods:
            print(f"---------- key: {key}, runtime: {runtime}")
            top_runtimes.append((key, runtime))
            cumulative_runtime += runtime

    other_runtime = total_runtime_value - cumulative_runtime

    print(f"Total runtime: {total_runtime_value}")
    print(f"Top runtime: {cumulative_runtime}")
    print(f"Other runtime: {other_runtime}")

    # Add the "Other" category
    if other_runtime > 0:
        top_runtimes.append(("Other", other_runtime))

    # Prepare data for plotting
    labels, sizes = zip(*top_runtimes)

    # Generate Pie Chart with labels on the side
    plt.figure(figsize=(15, 10))
    wedges, texts, autotexts = plt.pie(sizes, autopct='%1.1f%%', startangle=140)
    for i, text in enumerate(autotexts):
        text.set_text(f'{sizes[i]:.2f}')

    # Add a legend with the labels
    plt.legend(wedges, labels, title="Categories")

    plt.title("Parallel Runtime Distribution from OOPS Profiling Data", fontsize=16, fontweight='bold')
    plt.xlabel("Runtime (s)", fontsize=14)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.show()
else:
    print("No timing data found in the Parallel Timing Statistics section.")
