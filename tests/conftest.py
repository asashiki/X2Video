"""Shared fixtures for X2Video tests.

Add fixtures here as the pipeline grows. For now this file exists
so the tests/ directory is wired into the project structure.

To add a fixture that loads a sample config:

    import pytest
    from x2video.config.loader import load_config

    @pytest.fixture
    def sample_config(tmp_path):
        config_file = tmp_path / "test.toml"
        config_file.write_text('[curation]\ntop_n = 3\n')
        return load_config(str(config_file))
"""
