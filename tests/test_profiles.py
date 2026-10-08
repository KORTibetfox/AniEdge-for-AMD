import ast
from pathlib import Path
import unittest
from hq_stream import select_profile


class Profiles(unittest.TestCase):
    def setUp(self):
        self.source = {'width':640,'height':480,'fps':24,'par':1,'rotate':0}

    def test_supported_sd_uses_hq(self):
        self.assertEqual(select_profile(self.source),'pro-fast')

    def test_high_resolution_or_fps_retains_native_timing(self):
        for change in ({'width':1280,'height':720},{'width':2560,'height':1440,'fps':60},{'fps':60},{'fps':0}):
            with self.subTest(change=change):
                self.assertEqual(select_profile({**self.source,**change}),'hd')

    def test_hq_unsupported_geometry_uses_hd(self):
        for change in ({'width':639},{'par':1.1},{'rotate':90}):
            with self.subTest(change=change):
                self.assertEqual(select_profile({**self.source,**change}),'hd')
        self.assertEqual(select_profile(self.source,True),'hd')

    def test_python_sources_parse(self):
        for path in Path(__file__).resolve().parents[1].glob('*.py'):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
