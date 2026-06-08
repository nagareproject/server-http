.PHONY: doc tests

clean:
	@rm -rf build dist public
	@rm -rf src/*.egg-info
	@find src \( -name '*.py[co]' -o -name '__pycache__' \) -delete
	@rm -rf doc/_build/*

update-precommit:
	uvx pre-commit autoupdate

install: clean
	git init
	uvx pre-commit install
	${MAKE} update-precommit

tests:
	 python -m pytest

qa:
	uvx ruff check src
	uvx ruff format --check src

qa-fix:
	uvx ruff check --fix src
	uvx ruff format src

doc:
	uvx --from sphinx --with sphinx-rtd-theme sphinx-build -b html doc doc/_build

wheel:
	uv build --wheel
