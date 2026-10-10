def pytest_ignore_collect(collection_path, config):
    """Ignore all .txt files during collection to prevent UnicodeDecodeError."""
    return collection_path.suffix == ".txt"
