.PHONY: build clean

build:
	python3 generate_configs.py

clean:
	rm -rf configs/*
