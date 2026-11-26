#!/usr/bin/env python3

import argparse
import yaml
import matplotlib.pyplot as plt
import re
import numpy as np

def read_timers(file_path):

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

  return runtimes

def makepie(runtimes,methods):

  # Ensure there is data to plot
  if runtimes:
    # Sort by runtime in descending order
#   if nosort==True:
#      print ("not being sorted")
#      sorted_runtimes = runtimes.items()
#   else:
#      sorted_runtimes = sorted(runtimes.items(), key=lambda item: item[1], reverse=True)
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

    # Set figure dimensions
    plt.figure(figsize=(15, 10))
   
    # Generate Pie Chart with labels on the side
    wedges, texts, autotexts = plt.pie(sizes, autopct='%1.1f%%', startangle=140)
    for i, text in enumerate(autotexts):
        text.set_text(f'{sizes[i]:.2f}')
        if labels[i] == "Other":
           wedges[i].set_alpha(0.5)

    # Add a legend with the labels
    plt.legend(wedges, labels, title="Categories")
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    plt.title("Parallel Runtime Distribution from OOPS Profiling Data", fontsize=16, fontweight='bold')
    plt.xlabel("Runtime (s)", fontsize=14)
  else:
      print("No timing data found in the Parallel Timing Statistics section.")

def makebars(runtimes,methods,ax,width,offset,color,case):

  # Ensure there is data to plot
  if runtimes:
    # Sort by runtime in descending order
    sorted_runtimes = runtimes.items()

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
    ind = np.arange(len(labels))
    bars = ax.barh(ind+offset,sizes,width,color=color,label=case+f': {total_runtime_value:.1f}s')

    ax.set(yticks=ind+offset, yticklabels=labels, ylim=[2*width - 1, len(labels)])
    ax.legend()
    ax.set_title("Parallel Runtime Distribution from OOPS Profiling Data", fontsize=16, fontweight='bold')
    ax.set_xlabel("Runtime (s)", fontsize=14)

    # annotate bars with percentage times
    for i, this in enumerate(top_runtimes):
       p = 100 * this[1] / total_runtime_value
       ax.text(this[1] + 0.005*total_runtime_value, i+offset, f'{p:.1f}%\n', 
               color=color, fontweight='bold', fontsize=8, ha='left', va='top')
  else:
      print("No timing data found in the Parallel Timing Statistics section.")

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
plt_type = config['plot type']

if plt_type == 'pie':
  # make pie chart
  for file in file_path:
    runtimes = read_timers(file)
    makepie(runtimes,methods)

else:
  # read relevant additional attributes
  # make bar plots
  colors = config['bar attributes']['colors']
  labels = config['bar attributes']['labels']
  width =  config['bar attributes']['width']
  fig, ax = plt.subplots(figsize=(12, 8), gridspec_kw={'width_ratios': [2], 'height_ratios': [1]})
  for i, file in enumerate(file_path):
    runtimes = read_timers(file)
    offset = i*width
    makebars(runtimes,methods,ax,width,offset,colors[i],labels[i])
  plt.subplots_adjust(left=0.3) # labels tend to be long

plt.show()

