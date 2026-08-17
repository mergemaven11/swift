.PHONY: install test smoke build docker-build clean

install:
	python -m pip install -e '.[dev]'

test:
	python -m compileall -q swift_files main.py
	python -m pytest -q

smoke:
	python main.py --version
	python main.py doctor --json

build:
	python -m build

docker-build:
	docker build -t swiftfilez:local .

clean:
	rm -rf build dist *.egg-info .pytest_cache
