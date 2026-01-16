# JEDI Configuration Builder - GDAS Client

JCB-GDAS is a configuration client repository for the JEDI Configuration Builder (JCB) system used by NOAA-EMC for Global Data Assimilation System (GDAS) weather forecasting and data assimilation. It contains YAML Jinja2 templates for configuring JEDI algorithms, models, and observations.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Initial Setup and Dependencies
- Install Python 3.6+ and basic dependencies:
  ```bash
  python3 -m pip install --user pyyaml jinja2 click pytest
  ```

### JCB Development Environment Setup
- Clone and set up the main JCB repository with clients:
  ```bash
  cd /tmp
  git clone --branch develop --recursive https://github.com/NOAA-EMC/jcb.git jcb_repo  # Takes 30-60 seconds
  cd jcb_repo
  ./jcb_client_init.py  # Takes 2-3 minutes. NEVER CANCEL. Set timeout to 5+ minutes.
  python3 -m pip install --user .  # Takes 30-60 seconds
  ```
- The init script clones client repositories (jcb-gdas, jcb-rdas) and algorithms into `src/jcb/configuration/`
- **CRITICAL**: Always run from development directory with PYTHONPATH for local testing

### Testing and Validation
- Run client integration tests from JCB repo with proper PYTHONPATH:
  ```bash
  cd /tmp/jcb_repo
  PYTHONPATH=/tmp/jcb_repo/src pytest test/client_integration -v
  ```
  - Takes 15-20 seconds to complete. NEVER CANCEL.
  - Some tests may fail on .git directory checks - this is normal
  - Set timeout to 60+ seconds for safety

### Rendering JEDI Configurations
- Test configuration rendering using Python API:
  ```bash
  cd /tmp/jcb_repo
  PYTHONPATH=/tmp/jcb_repo/src python3 -c "
  import jcb
  import yaml
  config = yaml.safe_load(open('/path/to/gdas/templates.yaml'))
  result = jcb.render(config)
  print('Render successful')
  "
  ```
- The command-line interface requires development setup:
  ```bash
  cd /tmp/jcb_repo
  PYTHONPATH=/tmp/jcb_repo/src python3 -m jcb.driver render input.yaml output.yaml
  ```

## Validation

### Manual Validation Steps
- ALWAYS test configuration rendering after making changes to templates
- Run client integration tests to ensure templates are properly structured
- Validate YAML syntax for non-template files (.yaml):
  ```bash
  python3 -c "import yaml; yaml.safe_load(open('file.yaml'))"
  ```
- For template files (.yaml.j2), use JCB rendering to validate:
  ```bash
  cd /tmp/jcb_repo
  PYTHONPATH=/tmp/jcb_repo/src python3 -c "import jcb, yaml; config=yaml.safe_load(open('template_dict.yaml')); jcb.render(config)"
  ```
- Check template variable consistency across related files

### GitHub Workflow Validation
- The repository uses GitHub Actions for CI testing at `.github/workflows/run_jcb_basic_testing.yaml`
- Workflow clones main JCB repo, initializes clients, and runs integration tests
- Takes 3-5 minutes total. NEVER CANCEL.
- Set timeout to 10+ minutes for workflow commands

## Repository Structure

### Key Directories
- `algorithm/` - Data assimilation algorithm templates (3dvar, LETKF, etc.)
  - `atmosphere/` - Atmospheric DA algorithm configurations
  - `marine/`, `aero/`, `snow/` - Other domain-specific algorithms
- `model/` - Model configuration templates
  - `atmosphere/` - FV3-JEDI atmospheric model configs
  - Contains Jinja2 templates (.j2) for geometry, backgrounds, increments
- `observations/` - Observation operator templates
  - `atmosphere/` - Satellite and conventional observation configs
  - Individual files for each instrument/platform (e.g., abi_g17.yaml.j2)
- `observation_chronicle/` - Observation metadata and channel configurations
- `test/client_integration/` - Integration test templates and configurations

### File Naming Conventions
- All template files use `.yaml.j2` extension for Jinja2 templates
- Model templates must use `<component>_` prefix (e.g., `atmosphere_background.yaml.j2`)
- Observation files named by instrument/platform (e.g., `iasi_metop-a.yaml.j2`)

### Template Variables
- Variables follow naming pattern: `<component>_<variable_name>`
- Example: `atmosphere_background_path`, `marine_model_timestep`
- Template files in model/ directory MUST use component-prefixed variables

## Common Tasks

### Repository Directory Structure (for reference)
```
/home/runner/work/jcb-gdas/jcb-gdas/
├── .github/workflows/run_jcb_basic_testing.yaml  # CI workflow
├── algorithm/
│   ├── aero/, atmosphere/, marine/, obstats/, snow/
│   └── atmosphere/fv3jedi_fv3inc_lgetkf.yaml.j2  # Example algorithm
├── model/
│   ├── aero/, atmosphere/, marine/, snow/
│   └── atmosphere/atmosphere_background.yaml.j2  # Example model config
├── observations/
│   ├── aero/, atmosphere/, atmosphere-lgetkf/, marine/, snow/
│   └── atmosphere/iasi_metop-a.yaml.j2  # Example observation
├── observation_chronicle/
│   ├── atmosphere/, snow/
│   └── atmosphere/abi_g17.yaml  # Example chronicle metadata
└── test/client_integration/
    ├── gdas-atmosphere-templates.yaml  # Test template dictionary
    └── gdas-marine-templates.yaml
```

### Working with Templates
- Edit `.yaml.j2` files using standard text editors
- Variables use Jinja2 syntax: `{{ variable_name }}`
- Test rendering with sample template dictionaries from `test/client_integration/`
- Always validate template syntax before committing

### Adding New Observations
- Create new `.yaml.j2` file in appropriate `observations/<component>/` directory
- Follow existing naming patterns (instrument_platform.yaml.j2)
- Add corresponding metadata file in `observation_chronicle/` if needed
- Test rendering with existing template configurations

### Debugging Template Issues
- Check variable naming consistency across files
- Validate YAML structure after template rendering
- Use Python API for debugging: `jcb.render(template_dict)` returns rendered config
- Review client integration test output for template validation errors

## Important Notes

- **NEVER CANCEL** GitHub workflow runs - they may take 5+ minutes
- **NEVER CANCEL** client initialization - takes 2-3 minutes for git clones
- **NEVER CANCEL** integration tests - they may take 15-30 seconds but can appear to hang
- This is a configuration repository - no compilation/build process required
- Changes affect JEDI experiment configurations used in weather forecasting
- Template changes require integration testing with main JCB system
- Use development JCB setup for local testing and validation

## Troubleshooting

### Common Issues
- **"FileNotFoundError: configuration/apps"** - Run JCB from development directory with PYTHONPATH
- **"Template key does not start with component_"** - Ensure model templates use proper prefixed variables
- **"YAML scanner error in .j2 file"** - Don't validate .j2 templates with yaml.safe_load, use JCB rendering
- **Integration tests fail on .git directory** - This is normal, test still validates templates

### Performance Notes
- JCB client initialization: 2-3 minutes (git clones)
- Client integration tests: 15-30 seconds
- Configuration rendering: 1-5 seconds per template
- GitHub workflow: 3-5 minutes total

### Expected File Counts
- Algorithm templates: ~10 files per component
- Model templates: ~15 files per component
- Observation templates: ~50+ files in atmosphere/ (satellites, instruments)
- Observation chronicles: ~50+ metadata files