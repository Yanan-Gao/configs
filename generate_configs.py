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
from jinja2 import Environment, FileSystemLoader


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

env = Environment(loader=FileSystemLoader(TEMPLATE_ROOT))
env.globals.update(
    # Use a placeholder so date_time is resolved at run time
    date_time=DateTimePlaceholder(),
    audience_version_date_format='%Y%m%d',
    ttd_write_env=os.environ.get('TTD_WRITE_ENV', 'prod'),
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


def find_env_paths():
    """Return a set of environment paths defined in overrides."""
    env_paths = set()
    for root, _, files in os.walk(OVERRIDE_ROOT):
        for fname in files:
            if not fname.endswith('.yml'):
                continue
            rel = os.path.relpath(os.path.join(root, fname), OVERRIDE_ROOT)
            parts = rel.split(os.sep)
            if 'audience' not in parts:
                continue
            idx = parts.index('audience')
            env_dir = os.path.join(*parts[:idx])
            env_paths.add(env_dir.replace(os.sep, '/'))
    return env_paths


def generate_all():
    templates = find_templates()
    env_paths = find_env_paths()

    for env_path in env_paths:
        for t_path, template in templates.items():
            job_path = os.path.splitext(t_path)[0]  # e.g. audience/Job/config.yml
            if not job_path.startswith('audience/'):
                continue
            job_suffix = job_path[len('audience/'):]  # Job/config.yml

            override_file = os.path.join(OVERRIDE_ROOT, env_path, 'audience', job_suffix)
            data = {}
            if os.path.exists(override_file):
                with open(override_file) as f:
                    data = yaml.safe_load(f) or {}

            data.setdefault('environment', env_path)
            out_path = os.path.join(OUTPUT_ROOT, env_path, 'audience', job_suffix)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            rendered = template.render(**data)
            with open(out_path, 'w') as f:
                f.write(rendered)
            print(f'Wrote {out_path}')


if __name__ == '__main__':
    generate_all()
