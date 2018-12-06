import os
import pytest
import pytest_twisted as pt

from controller.settings import load_pools

@pytest.fixture(scope='module')
def pools(request):
    testdir  = request.fspath.dirname  # work in the test directory
    filename = os.path.join(testdir, './pools.json')

    return load_pools(filename)
