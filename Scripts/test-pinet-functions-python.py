#!python3
import os, sys
import shutil
import tempfile
import unittest

pinet_functions = __import__("pinet-functions-python")

class TestPiNet(unittest.TestCase):
   
    def setUp(self):
        super().setUp()
        pinet_functions.DATA_TRANSFER_FILEPATH = tempfile.mktemp()
        open(pinet_functions.DATA_TRANSFER_FILEPATH, "w").close()
        self.addCleanup(os.remove, pinet_functions.DATA_TRANSFER_FILEPATH)
    
class TestSupportFunctions(TestPiNet):
    
    LINES = [
        "Line 1\n",
        " Line 2\n",
        "Line 3 \n",
        "\n"
    ]
    
    def setUp(self):
        super().setUp()
        self.filepath = tempfile.mktemp()
        with open(self.filepath, "w") as f:
            f.writelines(self.LINES)
    
    def test_getTextFile(self):
        self.assertEqual(self.LINES, pinet_functions.getTextFile(self.filepath))

    def test_removeN(self):
        lines = list(self.LINES)
        self.assertEqual([l.rstrip("\n") for l in self.LINES], pinet_functions.removeN(lines))
    
    def test_blankLineRemover(self):
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
    
    def test_getReleaseChannel(self):
        branches = {
            "Stable" : "master",
            "Dev" : "dev"
        }
        filepath = tempfile.mktemp()
        for channel, branch in branches.items():
            with open(filepath, "w") as f:
                f.write("ReleaseChannel=%s\n" % channel)
            pinet_functions.getReleaseChannel(filepath)
            self.assertEqual(pinet_functions.ReleaseBranch, branch)

    def test_stripStartWhitespaces(self):
        lines = list(self.LINES)
        self.assertEqual(["Line 1\n", "Line 2\n", "Line 3 \n", ""], pinet_functions.stripStartWhitespaces(lines))

    def test_stripEndWhitespaces(self):
        lines = list(self.LINES)
        self.assertEqual(["Line 1", " Line 2", "Line 3", ""], pinet_functions.stripEndWhitespaces(lines))

    def test_cleanStrings(self):
        lines = list(self.LINES)
        self.assertEqual(["Line 1", "Line 2", "Line 3", ""], pinet_functions.cleanStrings(lines))

    def test_getCleanList(self):
        self.assertEqual(["Line 1", "Line 2", "Line 3", ""], pinet_functions.getCleanList(self.filepath))
        

class TestDownloads(TestPiNet):
    
    def setUp(self):
        self.url = "http://pinet.org.uk/"
        self.filepath = tempfile.mktemp()
        open(self.filepath, "w").close()
        self.addCleanup(os.remove, self.filepath)
    
    def test_downloadFile_ValidURL(self):
        result = pinet_functions.downloadFile(self.url, self.filepath)
        self.assertTrue(result)
        with open(self.filepath) as f:
            self.assertIn("PiNet, A system for setting up and managing a classroom set of Raspberry Pis", f.read())

    def test_downloadFile_InvalidURL(self):
        result = pinet_functions.downloadFile(self.url + "does-not-exist", self.filepath)
        self.assertFalse(result)

class TestVersions(TestPiNet):
    
    def test_compareVersions_local_gt_web(self):
        #
        # Strictly, this is undefined: at present the compare versions doesn't even
        # assume it will happen; and depending on the minor version numbers, it may give
        # true or false
        #
        #~ self.assertFalse(pinet_functions.compareVersions("1.0.0", "0.9.0"))
        pass
    
    def test_compareVersions_local_eq_web(self):
        self.assertFalse(pinet_functions.compareVersions("1.0.0", "1.0.0"))

    def test_compareVersions_local_lt_web(self):
        self.assertTrue(pinet_functions.compareVersions("1.0.0", "1.1.0"))

class TestConfigParameter(TestPiNet):
    
    def setUp(self):
        self.filepath = tempfile.mktemp()
        with open(self.filepath, "w") as f:
            f.write("version=1234\n")
    
    def test_getConfigParameter_present(self):
        self.assertEqual(pinet_functions.getConfigParameter(self.filepath, "version="), "1234")

    def test_getConfigParameter_not_present(self):
        self.assertEqual(pinet_functions.getConfigParameter(self.filepath, "not-present="), "None")

if __name__ == '__main__':
    unittest.main()
