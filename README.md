# Config Generation Tool

This repository demonstrates a simple configuration generation workflow using **Jinja2** templates and YAML overrides. Generated files are written into the `job-config` directory and should not be manually edited.

## Structure
```
config-templates/   # Jinja2 templates
config-overrides/   # Human-provided values
job-config/         # Generated output
```

The `generate_configs.py` script walks all override files and renders the matching template to produce a final config file.

## Usage
Install dependencies and run the generator:
```bash
pip install jinja2 PyYAML
python3 generate_configs.py
```
The script will populate `job-config` with rendered YAML files.
