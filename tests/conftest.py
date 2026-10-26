import pytest

from dqf.baseline import load_baseline
from dqf.loads import BATCH_ROWS, get_load, load_pool
from dqf.store import AuditStore, make_engine


@pytest.fixture(scope="session")
def baseline():
    return load_baseline(expected_rows=BATCH_ROWS)


@pytest.fixture(scope="session")
def pool(baseline):
    return load_pool(baseline)


@pytest.fixture()
def clean(pool):
    return get_load(pool, 0)


@pytest.fixture()
def store(tmp_path):
    return AuditStore(make_engine(f"sqlite:///{tmp_path / 'audit.db'}"))
