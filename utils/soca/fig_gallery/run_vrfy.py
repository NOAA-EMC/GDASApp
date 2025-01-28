from jinja2 import Template
import subprocess
from datetime import datetime, timedelta
import yaml
import sys
import copy
import os

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

    # Get the YAML configuration file name from the input argument
    if len(sys.argv) != 2:
        print("Usage: python run_vrfy.py <config.yaml>")
        sys.exit(1)

    config_file = sys.argv[1]

    # Read the YAML template from the file
    with open(config_file, "r") as file:
        yaml_template = file.read()

    # Load the template YAML as a dictionary
    template_dict = yaml.safe_load(yaml_template)

    # Render the template with Jinja2
    template = Template(yaml_template)
    config = yaml.safe_load(template.render(pslot=template_dict["pslot"]))

    # Iterate over the date range
    for pdy in iterate_pdy_range(config['start_pdy'], config['end_pdy']):
        context = copy.deepcopy(config)
        for cyc in config["cycs"]:
          # Update the cycle's date
          context.update({"pdy": pdy, "cyc": cyc})

          # Prepare the job card
          template_jobcard = os.path.join(context['homegdas'], 'utils', 'soca', 'fig_gallery', 'vrfy_jobcard.sh.j2')  # Assumes a Jinja2 template file in the moegdas directory
          jobcard = f"vrfy_jobcard.{context['pslot']}.{context['pdy']}.{context['cyc']}.sh"
          generate_jobcard(template_jobcard, jobcard, context)

          # Submit the plotting job
          subprocess.run(f"sbatch {jobcard}", shell=True)
