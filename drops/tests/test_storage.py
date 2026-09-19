import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from drops.storage import UploadTooLargeError, normalized_name, prepare_upload


class MisreportedUpload:
    name = "../../answer.txt"
    content_type = "text/plain"
    size = 1

    def chunks(self):
        yield b"1234"
        yield b"5678"


class StorageTests(SimpleTestCase):
    def test_name_removes_paths_and_controls(self):
        self.assertEqual(normalized_name("../folder\\bad\x00name.txt"), "badname.txt")

    def test_streamed_size_is_enforced_independently_of_claimed_size(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with override_settings(PRIVATE_FILES_DIR=root / "files"):
                with self.assertRaises(UploadTooLargeError):
                    prepare_upload(MisreportedUpload(), max_bytes=5)
                temporary = root / "files" / ".tmp"
                self.assertFalse(temporary.exists() and any(temporary.iterdir()))
