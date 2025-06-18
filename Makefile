group ?= all
env ?= all
exp ?= all

.PHONY: build clean

build:
	python3 generate_configs.py group=$(group) env=$(env) exp=$(exp)
clean:
	python -c "import shutil, os; shutil.rmtree('configs', ignore_errors=True); os.makedirs('configs', exist_ok=True)"
