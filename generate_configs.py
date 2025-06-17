import os
import sys
import subprocess
import importlib

# Ensure the script is executed with Python 3
if sys.version_info.major < 3:
    sys.stderr.write("This script requires Python 3.\n")
    sys.exit(1)


def ensure_dependency(pkg, import_name=None):
    """Install the given package if the import fails."""
    import_name = import_name or pkg
    try:
        importlib.import_module(import_name)
    except ImportError:
        print(f"Installing missing dependency {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


ensure_dependency("PyYAML", "yaml")
ensure_dependency("Jinja2", "jinja2")

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, exceptions


class DateTimePlaceholder:
    """Object that renders Jinja placeholders for date_time."""

    def __str__(self):
        return "{{ date_time }}"

    def strftime(self, fmt):
        # Preserve the formatting expression for run time resolution
        return f"{{{{ date_time.strftime('{fmt}') }}}}"

TEMPLATE_ROOT = 'config-templates'
OVERRIDE_ROOT = 'config-overrides'
OUTPUT_ROOT = 'configs'

# Each job group contains templates for individual jobs. Each job has two
# template files: ``behavioral_config.yml.j2`` and ``outputs.yml.j2``. These
# render directly to ``behavioral_config.yml`` and ``outputs.yml`` under
# ``configs`` with plain key/value pairs.

env = Environment(
    loader=FileSystemLoader(TEMPLATE_ROOT),
    undefined=StrictUndefined,
)
env.globals.update(
    # Use a placeholder so date_time is resolved at run time
    date_time=DateTimePlaceholder(),
    version_date_format='%Y%m%d',
)


def find_templates():
    templates = {}
    for root, _, files in os.walk(TEMPLATE_ROOT):
        for f in files:
            if f.endswith('.j2'):
                rel = os.path.relpath(os.path.join(root, f), TEMPLATE_ROOT)
                rel = rel.replace(os.sep, "/")  # ensure Jinja2-compatible separators
                templates[rel] = env.get_template(rel)
    return templates


def find_groups():
    """Return the list of top-level job groups under TEMPLATE_ROOT."""
    return [d for d in os.listdir(TEMPLATE_ROOT)
            if os.path.isdir(os.path.join(TEMPLATE_ROOT, d))]


def find_env_paths(group):
    """Return a set of environment paths defined in overrides for the group."""
    env_paths = set()
    for root, _, files in os.walk(OVERRIDE_ROOT):
        for fname in files:
            if not fname.endswith('.yml'):
                continue
            rel = os.path.relpath(os.path.join(root, fname), OVERRIDE_ROOT)
            parts = rel.split(os.sep)
            if group not in parts:
                continue
            idx = parts.index(group)
            env_dir = os.path.join(*parts[:idx])
            env_paths.add(env_dir.replace(os.sep, '/'))
    return env_paths


def generate_all():
    templates = find_templates()
    groups = find_groups()

    for group in groups:
        env_paths = find_env_paths(group)

        for env_path in env_paths:
            for t_path, template in templates.items():
                job_path = os.path.splitext(t_path)[0]
                if not job_path.startswith(f'{group}/'):
                    continue
                job_dir, filename = os.path.split(job_path)
                job_name = job_dir[len(f'{group}/'):]

                override_file = os.path.join(
                    OVERRIDE_ROOT,
                    env_path,
                    group,
                    job_name,
                    'config.yml',
                )

                data = {}
                if os.path.exists(override_file):
                    with open(override_file) as f:
                        data = yaml.safe_load(f) or {}

                data.setdefault('environment', env_path)
                # Use the top-level override directory (e.g. 'prod', 'experiment',
                # 'test') as the write environment for template paths.
                partition = env_path.split('/')[0]
                data.setdefault('ttd_write_env', partition)
                out_dir = os.path.join(OUTPUT_ROOT, env_path, group, job_name)
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, filename)
                try:
                    rendered = template.render(**data)
                except exceptions.UndefinedError as e:
                    message = str(e)
                    missing_key = None
                    if "'" in message:
                        parts = message.split("'")
                        if len(parts) >= 2:
                            missing_key = parts[1]
                    if missing_key:
                        print(
                            f"Error generating {env_path}/{job_name}/{filename}: "
                            f"configuration '{missing_key}' is required but no value was provided "
                            f"in {override_file}",
                            file=sys.stderr,
                        )
                    else:
                        print(
                            f"Error generating {env_path}/{job_name}/{filename}: {message}",
                            file=sys.stderr,
                        )
                    continue

                data_dict = yaml.safe_load(rendered) or {}
                # allow templates to include optional 'job_name' field but ignore it
                data_dict.pop('job_name', None)

                with open(out_path, 'w') as f:
                    yaml.safe_dump(
                        data_dict,
                        f,
                        sort_keys=False,
                    )
                print(f'Wrote {out_path}')


if __name__ == '__main__':
    generate_all()
