#!/usr/bin/env python3


# creates figures of timeseries from the csv outputs computed by gdassoca_obsstats.x
import argparse
from itertools import product
import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


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

    def plot_timeseries(self, ocean, variable):
        # Filter data for the given ocean and variable
        filtered_data = self.data[(self.data['Ocean'] == ocean) & (self.data['Variable'] == variable)]

        if filtered_data.empty:
            print("No data available for the given ocean and variable combination.")
            return

        # Get unique experiments
        experiments = filtered_data['Exp'].unique()

        # Plot settings
        fig, axs = plt.subplots(3, 1, figsize=(10, 15), sharex=True)
        fig.suptitle(f'{variable} statistics, {ocean} ocean', fontsize=16, fontweight='bold')

        for exp in experiments:
            exp_data = filtered_data[filtered_data['Exp'] == exp]

            # Plot RMSE
            axs[0].plot(exp_data['date'], exp_data['RMSE'], marker='o', linestyle='-', label=exp)
            axs[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H'))
            axs[0].xaxis.set_major_locator(mdates.DayLocator())
            axs[0].tick_params(labelbottom=False)
            axs[0].set_ylabel('RMSE')
            axs[0].legend()
            axs[0].grid(True)

            # Plot Bias
            axs[1].plot(exp_data['date'], exp_data['Bias'], marker='o', linestyle='-', label=exp)
            axs[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H'))
            axs[1].xaxis.set_major_locator(mdates.DayLocator())
            axs[1].tick_params(labelbottom=False)
            axs[1].set_ylabel('Bias')
            axs[1].legend()
            axs[1].grid(True)

            # Plot Count
            axs[2].plot(exp_data['date'], exp_data['Count'], marker='o', linestyle='-', label=exp)
            axs[2].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H'))
            axs[2].xaxis.set_major_locator(mdates.DayLocator())
            axs[2].set_ylabel('Count')
            axs[2].legend()
            axs[2].grid(True)

        # Improve layout and show plot
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(f'{dirout}/{inst}_{variable}_{ocean}.png')


if __name__ == "__main__":
    epilog = ["Usage examples: ./gdassoca_obsstats.py --exp gdas.*.csv"]
    parser = argparse.ArgumentParser(description="Observation space RMSE's and BIAS's",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=os.linesep.join(epilog))
    parser.add_argument("--exps", nargs='+', required=True,
                        help="Path to the experiment's COMROOT")
    parser.add_argument("--variable", required=True, help="ombg_qc or ombg_noqc")
    parser.add_argument("--figname", required=True, help="The name of the output figure")
    args = parser.parse_args()

    flist = []
    for exp in args.exps:
        print(exp)
        wc = exp + '/*.*/??/analysis/ocean/*.t??z.stats.csv'
        flist.append(glob.glob(wc))

    flist = sum(flist, [])
    obsStats = ObsStats()
    obsStats.read_csv(flist)
    for var, ocean in product(['ombg_noqc', 'ombg_qc'],
                              ['Atlantic', 'Pacific', 'Indian', 'Arctic', 'Southern']):
        obsStats.plot_timeseries(ocean, var)
