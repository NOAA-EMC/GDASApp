from jinja2 import Template
import subprocess
from datetime import datetime, timedelta

def iterate_pdy_range(start_pdy, end_pdy):
    """Generate a range of dates in YYYYMMDD format."""
    start_date = datetime.strptime(start_pdy, "%Y%m%d")
    end_date = datetime.strptime(end_pdy, "%Y%m%d")
    current_date = start_date

    while current_date <= end_date:
        yield current_date.strftime("%Y%m%d")
        current_date += timedelta(days=1)


def generate_jobcard(template_path, output_path, context):
    # Read the Jinja2 template file
    with open(template_path, 'r') as file:
        template_content = file.read()

    # Create a Jinja2 template object
    template = Template(template_content)

    # Render the template with custom values
    rendered_script = template.render(**context)

    # Write the rendered script to the output file
    with open(output_path, 'w') as file:
        file.write(rendered_script)

    print(f"Bash script generated at: {output_path}")

# Example usage
if __name__ == "__main__":

    # Define start and end dates
    start_pdy = "20210701"
    end_pdy = "20210702"

    # Iterate over the date range
    for pdy in iterate_pdy_range(start_pdy, end_pdy):
        for cyc in ["00", "06", "12", "18"]:
          # Custom values to update in the template
          context = {
              "pdy": pdy,
              "cyc": cyc,
              "run": "gdas",
              "pslot": "nomlb",
              "homegdas": "/work2/noaa/da/gvernier/runs/mlb/GDASApp"
          }

          # Additional context values for the job card
          context.update({
              "base_exp_path": f"/work2/noaa/da/gvernier/runs/mlb/{context['pslot']}/COMROOT/{context['pslot']}",
              "plot_ensemble_b": "OFF",
              "plot_parametric_b": "OFF",
              "plot_background": "OFF",
              "plot_increment": "ON",
              "plot_analysis": "OFF",
              "eva_plots": "ON",
              "qos": "batch",
              "hpc": "hercules",
              "eva_module": "EVA/orion",
          })

          # Prepare the job card
          template_jobcard = "vrfy_jobcard.sh.j2"  # Assumes a Jinja2 template file in the same directory
          jobcard = f"vrfy_jobcard.{context['pslot']}.{context['pdy']}.{context['cyc']}.sh"
          generate_jobcard(template_jobcard, jobcard, context)

          # Submit the plotting job
          subprocess.run(f"sbatch {jobcard}", shell=True)
