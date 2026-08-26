"""Example test — demonstrates the project's testing pattern.

Rename or delete this file once the first real test is written.
"""


def test_project_is_importable():
    """Sanity check that the package installs and imports cleanly."""
    import x2video

    assert x2video.__version__ == "0.1.0"


# Additional coverage lives in tests/test_pipeline.py and tests/test_config_loader.py.
