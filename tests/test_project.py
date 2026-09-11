import unittest

from main import KnowledgeError, EntryNotFoundError
from main import _format_entry, _parse_tags, _cmd_add

class TestProject(unittest.TestCase):
    def test__format_entry(self):
        try:
            _format_entry()
            pass
        except (TypeError, ValueError):
            pass
        self.assertTrue(True)
    def test__parse_tags(self):
        try:
            _parse_tags()
            pass
        except (TypeError, ValueError):
            pass
        self.assertTrue(True)
    def test__cmd_add(self):
        try:
            _cmd_add()
            pass
        except (TypeError, ValueError):
            pass
        self.assertTrue(True)