from jinja2 import Template, Environment
from datetime import datetime


def render_html(template_name, context):
    # Read the Jinja2 template file
    with open(template_name, 'r') as file:
        template_content = file.read()

    # Create a Jinja2 template object
    template = Template(template_content)

    # Render the template with custom values
    rendered_html = template.render(**context)

    # Write the rendered script to the output file
    with open('index.html', 'w') as file:
        file.write(rendered_html)

if __name__ == "__main__":
    context = {
        'year_list': ["2021", "2022"],
        'month_list': ["01", "02"],
        'day_list': ["01", "02", "03"],
        'pslot': "cp4.01"
    }
    render_html('index_vrfy_marine.html.j2', context)
