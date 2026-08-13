# testkit

Shared pytest fixtures and test assets for the [pysmo](https://github.com/pysmo/pysmo) and
[aimbat](https://github.com/pysmo/aimbat) test suites.

## Installation

This package is not published to PyPI. Install it directly from GitHub, pinned to a tag:

```bash
uv add "testkit @ git+https://github.com/pysmo/testkit@v0.1.0"
```

## Development

Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
make sync   # install deps
make lint   # ruff check + format --check
make mypy   # type check
make tests  # run the test suite
```
