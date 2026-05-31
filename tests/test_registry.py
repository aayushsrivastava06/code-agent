import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools import file_tools
from tools.registry import registry


def setup_module(module):
    # register file tools into the test registry
    file_tools.register_file_tools(lambda: '.')


def test_write_file_missing_content():
    res, ok = registry.call('write_file', {'path': 'tmp_test.txt'})
    assert not ok
    assert 'Missing required arguments' in res


def test_write_file_success(tmp_path):
    p = tmp_path / 'out.txt'
    res, ok = registry.call('write_file', {'path': str(p), 'content': 'hi'})
    assert ok
    assert 'Created' in res or 'Updated' in res
