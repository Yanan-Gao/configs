import os
import sys
import subprocess
import importlib
import datetime


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
                templates[rel] = env.get_template(rel)
    return templates


def generate_all():
    templates = find_templates()
    for root, _, files in os.walk(OVERRIDE_ROOT):
        for fname in files:
            if not fname.endswith('.yml'):
                continue
            override_path = os.path.join(root, fname)
            rel_override = os.path.relpath(override_path, OVERRIDE_ROOT)
            if not rel_override.startswith('audience' + os.sep):
                continue
            after_audience = rel_override[len('audience' + os.sep):]
            for t_path in templates:
                job_path = os.path.splitext(t_path)[0]  # e.g. audience/Job/config.yml
                if not job_path.startswith('audience' + os.sep):
                    continue
                job_suffix = job_path[len('audience' + os.sep):]
                if after_audience.endswith(job_suffix):
                    env_path = after_audience[:-len(job_suffix)].rstrip(os.sep)
                    out_path = os.path.join(OUTPUT_ROOT, 'audience', env_path, job_suffix)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open(override_path) as f:
                        data = yaml.safe_load(f) or {}
                    data.setdefault('environment', env_path)
                    rendered = templates[t_path].render(**data)
                    with open(out_path, 'w') as f:
                        f.write(rendered)
                    print(f'Wrote {out_path}')
                    break


if __name__ == '__main__':
    generate_all()
