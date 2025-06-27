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
    """Return the list of top-level job groups under ``TEMPLATE_ROOT``."""
    return [d for d in os.listdir(TEMPLATE_ROOT)
            if os.path.isdir(os.path.join(TEMPLATE_ROOT, d))]

def find_env_roots():
    """Return all environment paths (e.g. ``prod`` or ``experiment/exp1``)."""
    envs = []
    for env in os.listdir(OVERRIDE_ROOT):
        env_dir = os.path.join(OVERRIDE_ROOT, env)
        if not os.path.isdir(env_dir):
            continue
        if env in ("experiment", "test"):
            for exp in os.listdir(env_dir):
                exp_dir = os.path.join(env_dir, exp)
                if os.path.isdir(exp_dir):
                    envs.append(f"{env}/{exp}")
        else:
            envs.append(env)
    return envs


def find_groups_for_env(env_path):
    """Return groups that contain at least one override under ``env_path``."""
    groups = []
    base = os.path.join(OVERRIDE_ROOT, env_path)
    if not os.path.isdir(base):
        return groups
    for entry in os.listdir(base):
        group_dir = os.path.join(base, entry)
        if not os.path.isdir(group_dir):
            continue
        for root, _, files in os.walk(group_dir):
            if any(f.endswith('.yml') for f in files):
                groups.append(entry)
                break
    return groups


def generate_all(env_filter='all', exp_filter='all'):
    """Generate configuration files following the env -> exp layout.

    All groups that contain overrides under the selected environment are
    processed automatically.
    """
    if env_filter == 'all':
        exp_filter = 'all'
    templates = find_templates()
    env_paths = find_env_roots()
    if env_filter != 'all':
        env_paths = [p for p in env_paths if p.startswith(env_filter)]
        if not env_paths:
            print(f"Environment '{env_filter}' not found", file=sys.stderr)
            return

    for env_path in env_paths:
        parts = env_path.split('/')
        env_name = parts[0]
        exp_name = parts[1] if len(parts) > 1 else None
        if exp_filter != 'all' and exp_name != exp_filter:
            continue
        groups = find_groups_for_env(env_path)

        for group in groups:
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

                # Set default environment. Only non-prod environments include
                # the experiment name.
                data.setdefault('environment', env_name)
                if env_name in ("experiment", "test"):
                    data.setdefault('experimentName', exp_name)
                else:
                    data.pop('experimentName', None)
                # Default namespace for reading and writing data. Combine the
                # environment and experiment name when available.
                if exp_name:
                    partition = f"{env_name}/{exp_name}"
                else:
                    partition = env_name
                data.setdefault('data_namespace', partition)
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


def parse_cli_args(argv):
    """Parse simple key=value arguments from ``argv`` in env -> exp order."""
    env_name = None
    exp = None
    for arg in argv:
        if '=' in arg:
            key, value = arg.split('=', 1)
            if key == 'env':
                env_name = value
            elif key == 'exp':
                exp = value
    if env_name is None:
        print(
            "Usage: generate_configs.py env=<env|all> exp=<exp|all>",
            file=sys.stderr,
        )
        sys.exit(1)

    if env_name == 'all':
        if exp is not None:
            print(
                "When env=all, exp must not be provided",
                file=sys.stderr,
            )
            sys.exit(1)
        exp = 'all'
    elif env_name in ("experiment", "test"):
        if exp is None:
            print(
                "exp parameter is required when env is experiment or test",
                file=sys.stderr,
            )
            sys.exit(1)
        if exp == "":
            print("exp must not be empty", file=sys.stderr)
            sys.exit(1)
    elif env_name == "prod":
        if exp is not None:
            print("exp parameter is not allowed when env=prod", file=sys.stderr)
            sys.exit(1)
        exp = 'all'
    else:
        print(f"Unknown env '{env_name}'", file=sys.stderr)
        sys.exit(1)

    return env_name, exp


if __name__ == '__main__':
    env_name, exp = parse_cli_args(sys.argv[1:])
    generate_all(env_name, exp)
