"""Example test — demonstrates the project's testing pattern.

Rename or delete this file once the first real test is written.
"""


def test_project_is_importable():
    """Sanity check that the package installs and imports cleanly."""
    import x2video

    assert x2video.__version__ == "0.1.0"


# TODO(M3+): As each milestone adds business logic, add tests here or in
# dedicated test_<module>.py files:
#
#   tests/test_config_loader.py   — config discovery, TOML parsing, env overrides
#   tests/test_llm_client.py      — provider factory, mock API responses
#   tests/test_tts_client.py      — provider factory, edge-tts integration
#   tests/test_cli_fetch.py       — CLI arg parsing, config-driven defaults
#   …
#
# Install dev deps and run:  pip install -e ".[dev]" && pytest -v
