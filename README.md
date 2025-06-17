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
first directory level. Under each environment you can have one or more *group*
directories that contain related jobs. For example, overrides for the `prod`
environment might live under `config-overrides/prod/audience/` and the
generated files would be written to `configs/prod/audience/`. Future groups
such as `feature_store` or `kongming` can use the same pattern.

Each job template provides two files: `behavioral_config.yml.j2` for the
behavior-related settings and `outputs.yml.j2` for any output paths. Running the
generator renders these templates to `behavioral_config.yml` and `outputs.yml`
under the corresponding job directory. Each generated YAML file contains plain
key/value pairs.

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
