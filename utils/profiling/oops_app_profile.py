import matplotlib.pyplot as plt
import re

# Load the profiling data file
file_path = "oops_stats.txt"

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
            print(f"-------- {line}")
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

    for key, runtime in sorted_runtimes:
        if cumulative_runtime / total_runtime < 0.95:
            top_runtimes.append((key, runtime))
            cumulative_runtime += runtime
        else:
            other_runtime += runtime

    # Add the "Other" category
    if other_runtime > 0:
        top_runtimes.append(("Other", other_runtime))

    # Prepare data for plotting
    #print(top_runtimes)
    top_runtimes = [(key, size) for key, size in top_runtimes if "Total" not in key and "measured" not in key]
    labels, sizes = zip(*top_runtimes)
    print(f"sizes: {sizes}")
    print(f"labels: {labels}")

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
