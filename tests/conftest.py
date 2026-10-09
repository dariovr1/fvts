import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("VTS_NETWORK_TESTS") == "1":
        return
    skip_network = pytest.mark.skip(reason="set VTS_NETWORK_TESTS=1 to run network tests")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_network)
