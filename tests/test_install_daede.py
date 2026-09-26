"""Exercise the dedicated DAEDE installer using real local filesystem fixtures."""

import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SOURCE = {
    "repo": "kenzok8/openwrt-daede",
    "sha": "0b0e5d671e5748a060fbd79abc2f73733b09f902",
}
ANCHOR = "PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)"
HOST_DEPENDENCY = "PKG_BUILD_DEPENDS:=luci-base/host"
WINDOWS_SYMLINK_PRIVILEGE_ERROR = 1314


class InstallDaedeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((SCRIPTS / "install_daede.py").is_file(), "Installer is not implemented")
        self.installer = importlib.import_module("install_daede")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tree = self.root / "wrt"
        self.downloaded = self.root / "downloaded"
        self.feed = self.tree / "feeds/packages/net/daed"
        self.link = self.tree / "package/feeds/packages/daed"
        self.group = self.tree / "package/custom/kenzok8_openwrt-daede"
        self.write(self.feed / "Makefile", "original feed recipe\n")
        self.write(self.downloaded / "daed/Makefile", "maintained daemon recipe\n")
        self.write(self.downloaded / "daed/patches/001-fix.patch", "full patch contents\n")
        self.write(self.downloaded / "daed/files/daed.init", "service configuration\n")
        self.write(self.downloaded / "luci-app-daede/Makefile", ANCHOR + "\ninclude package.mk\n")
        self.write(self.downloaded / "luci-app-daede/root/usr/share/daede/view", "LuCI resource\n")
        self.write(self.downloaded / "dae/files/dae.config", "config dae 'config'\n")
        self.write(self.downloaded / "dae/Makefile", "unwanted DAE recipe\n")
        self.write(self.downloaded / "upgrade.sh", "unwanted upgrade script\n")

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))

    def symlink(self, target):
        self.link.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.link.symlink_to(os.path.relpath(target, self.link.parent), target_is_directory=True)
        except OSError as error:
            if getattr(error, "winerror", None) != WINDOWS_SYMLINK_PRIVILEGE_ERROR:
                raise
            self.skipTest("Windows lacks real symlink privilege; Linux CI must execute this test")

    def test_correct_feed_link_is_replaced_and_original_source_preserved(self):
        self.symlink(self.feed)
        record = self.installer.install_daede(self.tree, self.downloaded, SOURCE)
        self.assertFalse(self.link.is_symlink())
        self.assertFalse(self.link.exists())
        self.assertEqual((self.feed / "Makefile").read_text(), "original feed recipe\n")
        self.assertEqual((self.group / "daed/Makefile").read_text(), "maintained daemon recipe\n")
        self.assertEqual(record["repo"], SOURCE["repo"])
        self.assertEqual(record["sha"], SOURCE["sha"])
        self.assertEqual(record["replacement"]["removed_symlink"], "package/feeds/packages/daed")
        self.assertEqual(record["replacement"]["preserved_feed"], "feeds/packages/net/daed")
        self.assertEqual(record["adaptations"][0]["added"], HOST_DEPENDENCY)

    def test_wrong_link_target_is_rejected_without_mutation(self):
        wrong = self.tree / "feeds/packages/net/another-daemon"
        self.write(wrong / "Makefile", "preserve unrelated feed\n")
        self.symlink(wrong)
        with self.assertRaisesRegex(ValueError, "Unexpected DAED link target"):
            self.installer.install_daede(self.tree, self.downloaded, SOURCE)
        self.assertTrue(self.link.is_symlink())
        self.assertEqual(self.link.resolve(), wrong.resolve())
        self.assertFalse(self.group.exists())

    def test_real_directory_is_rejected_and_retained(self):
        self.write(self.link / "user-file", "must remain\n")
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            self.installer.install_daede(self.tree, self.downloaded, SOURCE)
        self.assertEqual((self.link / "user-file").read_text(), "must remain\n")
        self.assertFalse(self.group.exists())

    def test_missing_feed_link_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            self.installer.install_daede(self.tree, self.downloaded, SOURCE)
        self.assertFalse(self.group.exists())

    def test_full_daed_and_luci_payload_is_copied(self):
        self.installer.install_payload(self.downloaded, self.group)
        self.assertEqual((self.group / "daed/patches/001-fix.patch").read_text(), "full patch contents\n")
        self.assertEqual((self.group / "daed/files/daed.init").read_text(), "service configuration\n")
        resource = self.group / "luci-app-daede/root/usr/share/daede/view"
        self.assertEqual(resource.read_text(), "LuCI resource\n")

    def test_dae_contributes_only_the_required_config_resource(self):
        self.installer.install_payload(self.downloaded, self.group)
        copied = sorted(path.relative_to(self.group / "dae").as_posix()
                        for path in (self.group / "dae").rglob("*") if path.is_file())
        self.assertEqual(copied, ["files/dae.config"])
        self.assertEqual((self.group / "dae/files/dae.config").read_text(), "config dae 'config'\n")
        self.assertFalse((self.group / "upgrade.sh").exists())

    def test_host_dependency_is_added_only_to_the_copied_luci_recipe(self):
        recipe = self.downloaded / "luci-app-daede/Makefile"
        original = recipe.read_bytes()
        adaptations = self.installer.install_payload(self.downloaded, self.group)
        expected = original.replace(ANCHOR.encode(), (ANCHOR + "\n" + HOST_DEPENDENCY).encode())
        self.assertEqual((self.group / "luci-app-daede/Makefile").read_bytes(), expected)
        self.assertEqual(recipe.read_bytes(), original)
        self.assertEqual(adaptations[0]["added"], HOST_DEPENDENCY)

    def test_existing_custom_directory_is_not_overwritten(self):
        self.write(self.group / "keep", "previous work\n")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.installer.install_payload(self.downloaded, self.group)
        self.assertEqual((self.group / "keep").read_text(), "previous work\n")

    def test_host_dependency_anchor_does_not_rewrite_comment_text(self):
        comment = "# Example: " + ANCHOR + "\n"
        self.write(self.downloaded / "luci-app-daede/Makefile", comment + ANCHOR + "\n")
        self.installer.install_payload(self.downloaded, self.group)
        expected = comment + ANCHOR + "\n" + HOST_DEPENDENCY + "\n"
        self.assertEqual((self.group / "luci-app-daede/Makefile").read_text(), expected)

    def test_missing_source_file_fails_before_copying(self):
        for name in ("daed/Makefile", "luci-app-daede/Makefile", "dae/files/dae.config"):
            with self.subTest(name=name):
                path = self.downloaded / name
                original = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(ValueError, "Missing source file"):
                    self.installer.install_payload(self.downloaded, self.group)
                self.assertFalse(self.group.exists())
                path.write_bytes(original)

    def test_missing_or_duplicate_dependency_anchor_is_rejected(self):
        for content in ("include package.mk\n", ANCHOR + "\n" + ANCHOR + "\n"):
            with self.subTest(content=content):
                self.write(self.downloaded / "luci-app-daede/Makefile", content)
                with self.assertRaisesRegex(ValueError, "unique PKG_BUILD_DIR anchor"):
                    self.installer.install_payload(self.downloaded, self.group)
                self.assertFalse(self.group.exists())

    def test_existing_host_dependency_is_not_silently_duplicated(self):
        self.write(self.downloaded / "luci-app-daede/Makefile", ANCHOR + "\n" + HOST_DEPENDENCY)
        with self.assertRaisesRegex(ValueError, "already declares PKG_BUILD_DEPENDS"):
            self.installer.install_payload(self.downloaded, self.group)
        self.assertFalse(self.group.exists())

    def test_lock_requires_the_maintained_repository_and_full_commit(self):
        lock = self.root / "sources.json"
        for entry in (None, {}, SOURCE | {"repo": "other/repo"}, SOURCE | {"sha": "main"}):
            with self.subTest(entry=entry):
                lock.write_text(json.dumps({"daede": entry}), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "daede"):
                    self.installer.read_source_lock(lock)
        lock.write_text(json.dumps({"daede": SOURCE}), encoding="utf-8")
        self.assertEqual(self.installer.read_source_lock(lock), SOURCE)


if __name__ == "__main__":
    unittest.main()
