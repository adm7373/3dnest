# Contributing

## Development setup

```bash
python3 -m pip install -e ".[dev]"
```

## Before opening a pull request

Run the generator and checks locally:

```bash
python3 -m py_compile generate_nest.py
python3 generate_nest.py
git diff --check
pytest
```

Keep generated STL files intentional and explain substantial geometry changes
in the pull request. Do not commit caches, virtual environments, or temporary
rendering output.

Pull requests should describe the configuration changes, include relevant
preview images when geometry changes, and explain any known mesh limitations.
