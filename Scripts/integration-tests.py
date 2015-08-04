#!/usr/bin/env python3
import os, sys
import datetime
import shutil
import tempfile
import test.support
import unittest
import urllib.request as _urllib_request
import urllib.error as _urllib_error
import uuid

from feedparser import parse as _feedparser_parse

def _internet_is_available():
    try:
        _urllib_request.urlopen("http://pinet.org")
    except _urllib_error.URLError:
        return False
    else:
        return True
internet_is_available = False ## _internet_is_available()

def mock_urlopen(act_enabled, *args, **kwargs):
    """Allow the internet to appear to be available or not on demand
    """
    def _mock_urlopen(*args, **kwargs):
        if not act_enabled:
            raise _urllib_error.URLError("Internet is disabled")
    return _mock_urlopen

def mock_feedparser_parse(version):
    """Have feedparser.parse always read from a file of our choosing
    """
    def _mock_feedparser_parse(*args, **kwargs):
        with open("commits.xml") as f:
            xml = f.read().format(
                guid=uuid.uuid1(), 
                timestamp=datetime.datetime.now().isoformat(),
                release=version
            )
        return _feedparser_parse(xml)
    return _mock_feedparser_parse

def mock_do_nothing(*args, **kwargs):
    return None
    
pinet_functions = __import__("pinet-functions-python")

class TestPiNet(unittest.TestCase):

    text = [i + "\n" for i in "the quick brown fox".split()]
    
    def setUp(self):
        super().setUp()
        pinet_functions.DATA_TRANSFER_FILEPATH = tempfile.mktemp()
        open(pinet_functions.DATA_TRANSFER_FILEPATH, "w").close()
        self.addCleanup(os.remove, pinet_functions.DATA_TRANSFER_FILEPATH)
        
        self.originals = []
        self.addCleanup(self.replace_originals)
        
        self.filepath = tempfile.mktemp()
        with open(self.filepath, "w") as f:
            f.writelines(self.text)

    def track_original(self, object, attribute):
        value = getattr(object, attribute)
        self.originals.append((object, attribute, value))
    
    def replace_originals(self):
        for object, attribute, value in reversed(self.originals):
            setattr(object, attribute, value)
        
    def read_data(self):
        with open(pinet_functions.DATA_TRANSFER_FILEPATH) as f:
            return f.read()
    
class Test_replaceLineOrAdd(TestPiNet):
    """If oldstring is found in any part of a line in the input
    file, that entire line is replaced by newstring. If oldstring
    is not found at all, it is added to the end of the file
    """
    
    def test_replace_existing_line_entire_match(self):
        "oldstring matches entire line"
        pinet_functions.replaceLineOrAdd(self.filepath, "brown", "***")
        results = self.text[:2] + ["***\n"] + self.text[3:]
        with open(self.filepath) as f:
            self.assertEqual(list(f), results)
    
    def test_replace_existing_line_partial_match(self):
        "oldstring matches part of line"
        pinet_functions.replaceLineOrAdd(self.filepath, "bro", "***")
        results = self.text[:2] + ["***\n"] + self.text[3:]
        with open(self.filepath) as f:
            self.assertEqual(list(f), results)
    
    def test_add_new_line(self):
        "oldstring doesn't match any line"
        pinet_functions.replaceLineOrAdd(self.filepath, "@@@", "***")
        results = self.text + ["***\n"]
        with open(self.filepath) as f:
            self.assertEqual(list(f), results)

class Test_replaceBitOrAdd(TestPiNet):
    """If oldstring is found in any line, it is replaced in that line 
    by newstring. If oldstring is not found in any line nothing changes.
    """

    def test_replaceBitOrAdd_present(self):
        pinet_functions.replaceBitOrAdd(self.filepath, "row", "***")
        results = self.text[:2] + ["b***n\n"] + self.text[3:]
        with open(self.filepath) as f:
            self.assertEqual(list(f), results)

    def test_replaceBitOrAdd_not_present(self):
        pinet_functions.replaceBitOrAdd(self.filepath, "***", "@@@")
        results = list(self.text)
        with open(self.filepath) as f:
            self.assertEqual(list(f), results)

class Test_CheckInternet(TestPiNet):
    """Detect whether a useful internet connection is available by
    attempting to download from a set of known-good URLs.
    """

    def setUp(self):
        super().setUp()
        self.track_original(pinet_functions.urllib.request, "urlopen")
    
    def tearDown(self):
        super().tearDown()
    
    def test_internet_on(self):
        pinet_functions.urllib.request.urlopen = mock_urlopen(True)
        result = pinet_functions.internet_on(0)
        self.assertTrue(result)
        self.assertEqual(self.read_data(), "0")

    def test_internet_off(self):
        pinet_functions.urllib.request.urlopen = mock_urlopen(False)
        result = pinet_functions.internet_on(0)
        self.assertFalse(result)
        self.assertEqual(self.read_data(), "1")

class Test_checkUpdate(TestPiNet):
    """Determine whether a new version is available for download. If it
    is, offer a change log before downloading.
    """
    
    def setUp(self):
        super().setUp()
        self.track_original(pinet_functions.urllib.request, "urlopen")
        self.track_original(pinet_functions.feedparser, "parse")
        self.track_original(pinet_functions, "downloadFile")
        self.track_original(pinet_functions, "whiptailBox")
        self.track_original(pinet_functions, "whiptail")
        self.track_original(pinet_functions, "updatePiNet")
        
        #
        # Make sure downloadFile doesn't actually do anything, no matter
        # how many times it's called
        #
        pinet_functions.downloadFile = mock_do_nothing
    
    def tearDown(self):
        super().tearDown()

    def test_no_internet_available(self):
        pinet_functions.urllib.request.urlopen = mock_urlopen(False)
        pinet_functions.checkUpdate("1.1.1")
        self.assertEqual(self.read_data(), "0")
    
    def test_no_update_available(self):
        pinet_functions.urllib.request.urlopen = mock_urlopen(True)
        pinet_functions.feedparser.parse = mock_feedparser_parse("1.0.1")
        pinet_functions.checkUpdate("1.1.1")
        self.assertEqual(self.read_data(), "0")

    def test_update_available(self):
        pinet_functions.whiptailBox = mock_do_nothing
        pinet_functions.whiptail = mock_do_nothing
        #
        # We're not testing the actual update here, just the mechanism
        # for checking that there is an update to be had
        #
        pinet_functions.updatePiNet = mock_do_nothing
        pinet_functions.urllib.request.urlopen = mock_urlopen(True)
        pinet_functions.feedparser.parse = mock_feedparser_parse("1.0.1")
        pinet_functions.checkUpdate("0.9.1")
        self.assertEqual(self.read_data(), "1")

class Test_compareVersions(TestPiNet):
    """Compare the local version number to that on the web, returning
    True (and writing 1 to the output file) if an update is required.
    
    NB At present this function is known to be limited by its implementation:
    it assumes that each version has exactly three segments and that the
    web version is at least as up to date as the local version, ie you can't
    have a local version at 1.0.0 and a web version at 0.9.0
    """
    
    def test_web_is_newer(self):
        result = pinet_functions.compareVersions("1.0.0", "1.1.1")
        self.assertTrue(result)
        self.assertEqual(self.read_data(), "1")

    def test_web_is_not_newer(self):
        result = pinet_functions.compareVersions("1.0.0", "1.0.0")
        self.assertFalse(result)
        self.assertEqual(self.read_data(), "0")

class Test_checkIfFileContains(TestPiNet):
    """If string exists in filepath, write 1 to the output file, otherwise
    write 0
    """
    
    def test_file_contains_string(self):
        pinet_functions.checkIfFileContains(self.filepath, "brown")
        self.assertEqual(self.read_data(), "1")
        
    def test_file_does_not_contain_string(self):
        pinet_functions.checkIfFileContains(self.filepath, "***")
        self.assertEqual(self.read_data(), "0")


if False:

    class TestEntryPoints(TestPiNet):
        
        def test_no_args(self):
            assert False
        
        def test_updatePiNet(self):
            assert False

        def test_downloadFile(self):
            assert False

        def test_checkKernelFileUpdateWeb(self):
            assert False

        def test_checkKernelUpdater(self):
            assert False

        def test_installCheckKernelUpdater(self):
            assert False

        def test_previousImport(self):
            assert False

        def test_importFromCSV(self):
            assert False

        def test_installSoftwareList(self):
            assert False

        def test_installSoftwareList(self):
            assert False

        def test_installSoftwareFromFile(self):
            assert False

if __name__ == '__main__':
    unittest.main()
