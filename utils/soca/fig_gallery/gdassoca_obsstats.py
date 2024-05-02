#!/usr/bin/env python3


# creates figures of timeseries from the csv outputs computed by gdassoca_obsstats.x
import argparse
from itertools import product
import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

colors = [
    "lightsteelblue",
    "lightgreen",
    "lightpink",
    "lightsalmon",
    "lightcoral",
    "lightgoldenrodyellow",
    "paleturquoise",
    "palegreen",
    "palegoldenrod",
    "peachpuff",
    "mistyrose",
    "lavender"
]


class ObsStats:
    def __init__(self):
        self.data = pd.DataFrame()

    def read_csv(self, filepaths):
        # Iterate through the list of file paths and append their data
        for filepath in filepaths:
            new_data = pd.read_csv(filepath)

            # Convert date to datetime for easier plotting
            new_data['date'] = pd.to_datetime(new_data['date'], format='%Y%m%d%H')
            self.data = pd.concat([self.data, new_data], ignore_index=True)
            self.data.sort_values('date', inplace=True)

    def plot_timeseries(self, ocean, variable, inst="", dirout=""):
        # Filter data for the given ocean and variable
        filtered_data = self.data[(self.data['Ocean'] == ocean) & (self.data['Variable'] == variable)]
        if filtered_data.empty:
            print("No data available for the given ocean and variable combination.")
            return

        # Get unique experiments
        experiments = filtered_data['Exp'].unique()

        # Plot settings
        fig, axs = plt.subplots(3, 1, figsize=(10, 15), sharex=True)
        fig.suptitle(f'{inst} {variable} statistics, {ocean} ocean', fontsize=16, fontweight='bold')

        exp_counter = 0
        for exp in experiments:
            exp_data = self.data[(self.data['Ocean'] == ocean) &
                                 (self.data['Variable'] == variable) &
                                 (self.data['Exp'] == exp)]

            # Plot RMSE
            axs[0].plot(exp_data['date'], exp_data['RMSE'], marker='o', linestyle='-', color=colors[exp_counter], label=exp)
            axs[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H'))
            axs[0].xaxis.set_major_locator(mdates.DayLocator())
            axs[0].tick_params(labelbottom=False)
            axs[0].set_ylabel('RMSE')
            axs[0].legend()
            axs[0].grid(True)

            # Plot Bias
            axs[1].plot(exp_data['date'], exp_data['Bias'], marker='o', linestyle='-', color=colors[exp_counter], label=exp)
            axs[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H'))
            axs[1].xaxis.set_major_locator(mdates.DayLocator())
            axs[1].tick_params(labelbottom=False)
            axs[1].set_ylabel('Bias')
            axs[1].grid(True)

            # Plot Count
            axs[2].plot(exp_data['date'], exp_data['Count'], marker='o', linestyle='-', color=colors[exp_counter], label=exp)
            axs[2].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H'))
            axs[2].xaxis.set_major_locator(mdates.DayLocator())
            axs[2].set_ylabel('Count')
            axs[2].grid(True)

        # Improve layout and show plot
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(f'{dirout}/{inst}_{variable}_{ocean}.png')

if __name__ == "__main__":
    epilog = ["Usage examples: ./gdassoca_obsstats.py --exps cp1/COMROOT/cp1 cp2/COMROOT/cp2 --inst sst_abi_g16_l3c --dirout cp1vscp2"]
    parser = argparse.ArgumentParser(description="Observation space RMSE's and BIAS's",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=os.linesep.join(epilog))
    parser.add_argument("--exps", nargs='+', required=True,
                        help="Path to the experiment's COMROOT")
    parser.add_argument("--inst", required=True, help="The name of the instrument/platform (ex: sst_abi_g16_l3c)")
    parser.add_argument("--dirout", required=True, help="Output directory")
    args = parser.parse_args()

    flist = []
    inst = args.inst
    os.makedirs(args.dirout, exist_ok=True)

    for exp in args.exps:
        wc = exp + f'/*.*/??/analysis/ocean/*{inst}*.stats.csv'
        flist.append(glob.glob(wc))

    flist = sum(flist, [])
    obsStats = ObsStats()
    obsStats.read_csv(flist)
    for var, ocean in product(['ombg_noqc', 'ombg_qc'],
                              ['Atlantic', 'Pacific', 'Indian', 'Arctic', 'Southern']):
        obsStats.plot_timeseries(ocean, var, inst=inst, dirout=args.dirout)
