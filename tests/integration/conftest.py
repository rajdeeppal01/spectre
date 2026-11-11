import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests against live local services",
    )


def pytest_runtest_setup(item):
    if item.get_closest_marker("integration"):
        if not item.config.getoption("--run-integration", default=False):
            pytest.skip("Pass --run-integration to run integration tests against live services")
