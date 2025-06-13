# Config Generation Tool

This repository demonstrates a simple configuration generation workflow using **Jinja2** templates and YAML overrides. Generated files are written into the `configs` directory and should not be manually edited.

## Requirements

* Python 3
* `make`

## Structure
```
config-templates/   # Jinja2 templates
config-overrides/   # Human-provided values
configs/            # Generated output
```

Override files and generated configs are organized with the environment as the
first directory level. For example, overrides for the `prod` environment live
under `config-overrides/prod/audience/` and generated files are written to
`configs/prod/audience/`.

The `generate_configs.py` script walks all override files and renders the matching template to produce a final config file.

## Usage
Run the generator:
```bash
make build
```
The `generate_configs.py` script automatically installs `Jinja2` and `PyYAML` if they
are missing. The `build` target runs the script and populates `configs` with rendered YAML files.
You can clean out generated files with:
```bash
make clean
```
The clean target uses Python so it works on Windows as well as Unix-like systems.
