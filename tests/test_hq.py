import ast
import io
from pathlib import Path
import unittest
from hq_stream import read_frame, validate_source


class HQ(unittest.TestCase):
    def setUp(self):
        self.source = {'width': 640, 'height': 480, 'fps': 24, 'par': 1, 'rotate': 0}

    def test_supported_input_bounds(self):
        for change in ({}, {'width': 1280, 'height': 720, 'fps': 60}):
            with self.subTest(change=change):
                validate_source({**self.source, **change})

    def test_unsupported_input_is_rejected(self):
        for change in ({'width': 2560, 'height': 1440}, {'width': 639},
                       {'height': 0}, {'width': -2}, {'fps': 0}, {'fps': 61},
                       {'fps': float('nan')}, {'par': 1.1}, {'rotate': 90}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_source({**self.source, **change})

    def test_partial_frame_is_not_silently_discarded(self):
        self.assertEqual(read_frame(io.BytesIO(b'abc'), 3), b'abc')
        self.assertIsNone(read_frame(io.BytesIO(), 3))
        with self.assertRaises(RuntimeError):
            read_frame(io.BytesIO(b'ab'), 3)

    def test_python_sources_parse(self):
        for path in Path(__file__).resolve().parents[1].glob('*.py'):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
