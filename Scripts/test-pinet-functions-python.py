#!python3
import tempfile
import unittest
pinet_functions = __import__("pinet-functions-python")

class MockFile(object):
    
    def __init__(self, lines):
        self.lines = lines
        self.iterline = iter(lines)
    
    def readline():
        try:
            return next(self.iterline)
        except StopIteration:
            return None

def MockOpen(object):
    
    def __init__(self, lines):
        self.lines = lines
    
    def __call__(self, filepath):
        return MockFile(self.lines)

class TestPiNet(unittest.TestCase):
    
    pass
    
class TestSupportFunctions(TestPiNet):
    
    LINES = [
        "Line 1\n",
        " Line 2\n",
        "Line 3 \n",
        "\n"
    ]
    
    def setUp(self):
        self.filepath = tempfile.mktemp()
        with open(self.filepath, "w") as f:
            f.writelines(self.LINES)
    
    def test_getTextFile(self):
        self.assertEqual(self.LINES, pinet_functions.getTextFile(self.filepath))

    def test_removeN(self):
        self.assertEqual([l.rstrip("\n") for l in self.LINES], pinet_functions.removeN(self.LINES))
    
    def test_blankLineRemover(self):
        #
        # Strictly, at the moment this function only removes lines which contain nothing
        # but spaces. It ignores lines which contain nothing!
        #
        lines = ["Line 1", " Line 2 ", "", " "]
        self.assertEqual(["Line 1", " Line 2 "], pinet_functions.blankLineRemover(lines))

    def test_writeTextFile(self):
        filepath = tempfile.mktemp()
        lines = ["Line %d" % i for i in range(3)]
        pinet_functions.writeTextFile(lines, filepath)
        with open(filepath) as f:
            self.assertEqual("\n".join(lines) + "\n", f.read())
    
    def test_getList(self):
        self.assertEqual([l.strip("\n") for l in self.LINES], pinet_functions.getList(self.filepath))

    def test_findReplaceAnyLine(self):
        self.assertEqual(
            ["Line 1", "***", "Line 3"], 
            pinet_functions.findReplaceAnyLine(["Line 1", "Line 2", "Line 3"], "Line 2", "***")
        )

    def test_findReplaceSection(self):
        self.assertEqual(
            ["Line 1", "Li***", "Line 3"], 
            pinet_functions.findReplaceSection(["Line 1", "Line 2", "Line 3"], "ne 2", "***")
        )

if __name__ == '__main__':
    unittest.main()
