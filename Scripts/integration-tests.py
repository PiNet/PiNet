#!/usr/bin/env python3
import os, sys
import configparser
import contextlib
import datetime
import shutil
import tempfile
import test.support
import unittest
import urllib.request as _urllib_request
import urllib.error as _urllib_error
import urllib.parse
import uuid
import warnings

from feedparser import parse as _feedparser_parse

#
# Set up global config for use, eg, to skip destructive tests
# or to limit long-running ones, or to set up monkeypatches.
#
HERE = os.path.dirname(__file__)
NAME, _ = os.path.splitext(os.path.basename(__file__))
config = configparser.ConfigParser()
config.read(os.path.join(HERE, NAME + ".ini"))

suppress_warnings = bool(int(config.get("testing", "suppress_warnings")))
use_internet = bool(int(config.get("testing", "use_internet")))
i_am_root = os.geteuid() == 0

def _internet_is_available():
    try:
        _urllib_request.urlopen("http://example.com")
    except _urllib_error.URLError:
        return False
    else:
        return True
internet_is_available = use_internet and _internet_is_available()

def mock_urlopen(act_enabled, *args, **kwargs):
    """Allow the internet to appear to be available or not on demand
    """
    def _mock_urlopen(*args, **kwargs):
        print("_mock_urlopen called with", args, kwargs)
        if not act_enabled:
            raise _urllib_error.URLError("Internet is disabled")
    return _mock_urlopen

def mock_feedparser_parse(version):
    """Have feedparser.parse always read from a file of our choosing
    """
    def _mock_feedparser_parse(*args, **kwargs):
        with open(os.path.join(HERE, "commits.xml")) as f:
            xml = f.read().format(
                guid=uuid.uuid1(), 
                timestamp=datetime.datetime.now().isoformat(),
                release=version
            )
        return _feedparser_parse(xml)
    return _mock_feedparser_parse

def make_web_filepath(web_dirpath, url):
    "Turn url into a filepath rooted at web_dirpath"
    parsed = urllib.parse.urlparse(url)
    return os.path.join(web_dirpath, parsed.netloc, parsed.path.lstrip(os.path.sep))

def make_local_filepath(local_dirpath, filepath):
    "Turn filepath into a local filepath rooted at local_dirpath"
    return os.path.join(local_dirpath, filepath.lstrip(os.path.sep))

def mock_downloadFile(web_dirpath, local_dirpath):
    """Mock out the downloadFile routine by having it source from a local
    setup and write to a temp area
    """
    def _mock_downloadFile(url, filepath):
        web_filepath = make_web_filepath(web_dirpath, url)
        local_filepath = make_local_filepath(local_dirpath, filepath)
        os.makedirs(os.path.dirname(local_filepath), exist_ok=True)
        shutil.copyfile(web_filepath, local_filepath)
    return _mock_downloadFile

def mock_do_nothing(*args, **kwargs):
    return None

def mock_return_zero(*args, **kwargs):
    with open(pinet_functions.DATA_TRANSFER_FILEPATH, "w") as f:
        f.write("0")
    return 0
    
def suppress_whiptail(func):
    def _suppress_whiptail(*args, **kwargs):
        original_whiptailBox = pinet_functions.whiptailBox
        original_whiptail = pinet_functions.whiptail
        pinet_functions.whiptailBox = mock_return_zero
        pinet_functions.whiptail = mock_return_zero
        try:
            return func(*args, **kwargs)
        finally:
            pinet_functions.whiptail = original_whiptail
            pinet_functions.whiptailBox = original_whiptailBox
    return _suppress_whiptail

def remove(filepath):
    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass

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
    
class Test_replace_line_or_add(TestPiNet):
    """If oldstring is found in any part of a line in the input
    file, that entire line is replaced by newstring. If oldstring
    is not found at all, it is added to the end of the file
    """
    
    def test_replace_existing_line_entire_match(self):
        "oldstring matches entire line"
        pinet_functions.replace_line_or_add(self.filepath, "brown", "***")
        results = self.text[:2] + ["***\n"] + self.text[3:]
        with open(self.filepath) as f:
            self.assertEqual(list(f), results)
    
    def test_replace_existing_line_partial_match(self):
        "oldstring matches part of line"
        pinet_functions.replace_line_or_add(self.filepath, "bro", "***")
        results = self.text[:2] + ["***\n"] + self.text[3:]
        with open(self.filepath) as f:
            self.assertEqual(list(f), results)
    
    def test_add_new_line(self):
        "oldstring doesn't match any line"
        pinet_functions.replace_line_or_add(self.filepath, "@@@", "***")
        results = self.text + ["***\n"]
        with open(self.filepath) as f:
            self.assertEqual(list(f), results)

class Test_replace_bit_or_add(TestPiNet):
    """If oldstring is found in any line, it is replaced in that line 
    by newstring. If oldstring is not found in any line nothing changes.
    """

    def test_replace_bit_or_add_present(self):
        pinet_functions.replace_bit_or_add(self.filepath, "row", "***")
        results = self.text[:2] + ["b***n\n"] + self.text[3:]
        with open(self.filepath) as f:
            self.assertEqual(list(f), results)

    def test_replace_bit_or_add_not_present(self):
        pinet_functions.replace_bit_or_add(self.filepath, "***", "@@@")
        results = list(self.text)
        with open(self.filepath) as f:
            self.assertEqual(list(f), results)

class Test_CheckInternet(TestPiNet):
    """Detect whether a useful internet connection is available by
    attempting to download from a set of known-good URLs.
    
    NB This test doesn't actually need a connection to the internet
    because we're mocking urlopen to fake the results
    """

    def setUp(self):
        super().setUp()
        self.track_original(pinet_functions.urllib.request, "urlopen")
    
    def test_internet_on(self):
        pinet_functions.urllib.request.urlopen = mock_urlopen(True)
        result = pinet_functions.internet_on()
        self.assertTrue(result)
        self.assertEqual(self.read_data(), "0")

    def test_internet_off(self):
        pinet_functions.urllib.request.urlopen = mock_urlopen(False)
        result = pinet_functions.internet_on()
        self.assertFalse(result)
        self.assertEqual(self.read_data(), "1")

if False:
    
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

if False:
    
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

if False:
    
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
    
    @unittest.skipUnless(internet_is_available, "No internet available")
    class Test_downloadFile(TestPiNet):
        """Download a file and write to a position on the file system and
        return True if successful, False otherwise.
        
        Although this isn't strictly an entry-point it's used so frequently
        elsewhere (and mocked out for testing) that we'll test it works, as
        long as the internet is available
        """
        
        def setUp(self):
            super().setUp()
            self.download_filepath = tempfile.mktemp()
            self.addCleanup(remove, self.download_filepath)
            self.track_original(pinet_functions.urllib.request, "urlopen")
        
        def test_successful_download(self):
            result = pinet_functions.downloadFile("http://example.com", self.download_filepath)
            self.assertTrue(result)
            with open(self.download_filepath) as f:
                self.assertIn("Example Domain", f.read())

        def test_unsuccessful_download(self):
            pinet_functions.urllib.request.urlopen = mock_urlopen(False)
            result = pinet_functions.downloadFile("http://example.com", self.download_filepath)
            self.assertFalse(result)

class MockFilesystemMixin:

    def setUp(self):
        super().setUp()
        self.local_dirpath = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.local_dirpath)
    
    def make_local_filepath(self, filepath):
        "Turn filepath into a local filepath rooted at local_dirpath"
        return os.path.join(self.local_dirpath, filepath.lstrip(os.path.sep))
    
if False:
    
    class TestDownloads(MockFilesystemMixin, TestPiNet):
        
        def setUp(self):
            super().setUp()
            dirpath = tempfile.mkdtemp()
           
            #
            # Set up a fake download scheme where files are "uploaded"
            # from one area of a temporary directory and "downloaded"
            # to another.
            #
            self.web_dirpath = os.path.join(dirpath, "web")
            os.mkdir(self.web_dirpath)
            self.addCleanup(shutil.rmtree, dirpath)
            self.track_original(pinet_functions, "downloadFile")
            pinet_functions.downloadFile = self.mock_downloadFile()

        def make_web_filepath(self, url):
            "Turn url into a filepath rooted at web_dirpath"
            parsed = urllib.parse.urlparse(url)
            return os.path.join(self.web_dirpath, parsed.netloc, parsed.path.lstrip(os.path.sep))

        def mock_downloadFile(self):
            """Mock out the downloadFile routine by having it source from a local
            setup and write to a temp area
            """
            def _mock_downloadFile(url, filepath):
                web_filepath = self.make_web_filepath(url)
                local_filepath = self.make_local_filepath(filepath)
                os.makedirs(os.path.dirname(local_filepath), exist_ok=True)
                shutil.copyfile(web_filepath, local_filepath)
            return _mock_downloadFile
            
        def touch_web_file(self, url):
            web_filepath = self.make_web_filepath(url)
            os.makedirs(os.path.dirname(web_filepath), exist_ok=True)
            with open(web_filepath, "w") as f:
                f.write(url)

if False:
    
    class Test_updatePiNet(TestDownloads):
         
        def setUp(self):
            super().setUp()
             
            self.touch_web_file(pinet_functions.PINET_DOWNLOAD_URL)
            self.touch_web_file(pinet_functions.PINET_PYTHON_DOWNLOAD_URL)
        
        def test_updatePiNet(self):
            pinet_functions.updatePiNet()
            
            pinet_binary_filepath = os.path.join(pinet_functions.PINET_BINPATH, pinet_functions.PINET_BINARY)
            with open(self.make_local_filepath(pinet_binary_filepath)) as f:
                self.assertEqual(f.read(), pinet_functions.PINET_DOWNLOAD_URL)
            
            pinet_python_binary_filepath = os.path.join(pinet_functions.PINET_BINPATH, pinet_functions.PINET_PYTHON_BINARY)
            with open(self.make_local_filepath(pinet_python_binary_filepath)) as f:
                self.assertEqual(f.read(), pinet_functions.PINET_PYTHON_DOWNLOAD_URL)

if False:

    class Test_importFromCSV(TestPiNet):
        
        def setUp(self):
            super().setUp()
            
            self.track_original(pinet_functions, "create_user")
            self.track_original(pinet_functions, "add_user_to_group")
            self.mocked_users = {}
            self.mocked_user_groups = {}
            pinet_functions.create_user = self.mock_create_user()
            pinet_functions.add_user_to_group = self.mock_add_user_to_group()
            
            self.valid_csv_filepath = tempfile.mktemp()
            self.addCleanup(os.remove, self.valid_csv_filepath)
            self.invalid_csv_filepath = tempfile.mktemp()
            self.addCleanup(os.remove, self.invalid_csv_filepath)
            
            with open(self.valid_csv_filepath, "w") as f:
                f.write("username1,password1\n")
                f.write("username2,password2\n")
            
            with open(self.invalid_csv_filepath, "w") as f:
                f.write("user name1,password1\n")
                f.write("user name2,password2\n")
        
        def mock_create_user(self):
            def _mock_create_user(username, password):
                self.mocked_users[username] = password
            return _mock_create_user
        
        def mock_add_user_to_group(self):
            def _mock_add_user_to_group(username, group):
                self.mocked_user_groups.setdefault(username, []).append(group)
            return _mock_add_user_to_group
        
        @suppress_whiptail        
        def test_import_from_valid_file(self):
            pinet_functions.importFromCSV(self.valid_csv_filepath, "PASSWORD", True)
            self.assertEquals(
                self.mocked_users, 
                {
                    "username1" : pinet_functions.encrypted_password("password1"),
                    "username2" : pinet_functions.encrypted_password("password2"),
                }
            )
            for username, groups in self.mocked_user_groups.items():
                self.assertEquals(groups, pinet_functions.PINET_USER_GROUPS)
            self.assertEquals(self.read_data(), "0")
        
if False:
    
    @unittest.skipUnless(i_am_root, "Must be root to run this tests - it reads from /etc/shadow")
    class Test_previousImport(MockFilesystemMixin, TestPiNet):
        
        MIGRATIONS = {
            "shadow" : "{guid}:!:1:0:99999:1:::\n",
            "passwd" : "{guid}:x:0:0:root:/root:/bin/bash\n",
            "gshadow" : "{guid}:!:1:0:99999:7:::\n",
            "group" : "{guid}:x:0:\n"
        }
        
        def setUp(self):
            super().setUp()
            
            self.track_original(pinet_functions, "writeTextFile")
            self._original_writeTextFile = pinet_functions.writeTextFile
            pinet_functions.writeTextFile = self.mock_writeTextFile
            
            self.migration_dirpath = os.path.join(self.local_dirpath, "etc")
            os.makedirs(self.migration_dirpath)
            
            guid = uuid.uuid1()
            self.migrations = []
            for filename, entry in self.MIGRATIONS.items():
                filepath = os.path.join(self.migration_dirpath, filename + ".mig") 
                migrated_entry = entry.format(guid=guid)
                with open(filepath, "w") as f:
                    f.write(migrated_entry)
                self.migrations.append((filename, migrated_entry))
            
        def mock_writeTextFile(self, textlist, filepath):
            return self._original_writeTextFile(textlist, self.make_local_filepath(filepath))
        
        def test_import(self):
            """Attempt to import from a set of migrated files. Each migrated file
            consists of just one entry with a GUID unique across all test runs.
            This should end up at the end of the corresponding local file.
            """
            pinet_functions.previousImport(self.migration_dirpath)
            for filename, entry in self.migrations:
                filepath = os.path.join(self.migration_dirpath, filename)
                print(filepath)
                with open(filepath) as f:
                    lines = list(f)
                self.assertEquals(lines[-1], entry)

if False:

    class TestEntryPoints(TestPiNet):
        
        def test_no_args(self):
            assert False
        
        def test_checkKernelFileUpdateWeb(self):
            assert False

        def test_checkKernelUpdater(self):
            assert False

        def test_installCheckKernelUpdater(self):
            assert False

        def test_installSoftwareList(self):
            assert False

        def test_installSoftwareList(self):
            assert False

        def test_installSoftwareFromFile(self):
            assert False

if __name__ == '__main__':
    stdout_logpath = os.path.join(HERE, "%s.log" % NAME)
    with open(stdout_logpath, "w") as logfile:
        with contextlib.redirect_stdout(logfile):
            with tempfile.TemporaryDirectory() as d:
                import pinet_functions_python as pinet_functions
                pinet_functions.PINET_LOG_DIRPATH = d
                unittest.main(warnings="ignore" if suppress_warnings else None)
