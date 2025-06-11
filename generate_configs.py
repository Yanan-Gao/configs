import os
import yaml
from jinja2 import Environment, FileSystemLoader

TEMPLATE_ROOT = 'config-templates'
OVERRIDE_ROOT = 'config-overrides'
OUTPUT_ROOT = 'job-config'

env = Environment(loader=FileSystemLoader(TEMPLATE_ROOT))


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
