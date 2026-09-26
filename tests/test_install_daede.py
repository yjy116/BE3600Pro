"""Exercise the dedicated DAEDE installer using real local filesystem fixtures."""

import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SERVICE_FIXTURES = Path(__file__).resolve().parent / "fixtures/daede"
sys.path.insert(0, str(SCRIPTS))
SOURCE = {
    "repo": "kenzok8/openwrt-daede",
    "sha": "0b0e5d671e5748a060fbd79abc2f73733b09f902",
}
ANCHOR = "PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)"
HOST_DEPENDENCY = "PKG_BUILD_DEPENDS:=luci-base/host"
WINDOWS_SYMLINK_PRIVILEGE_ERROR = 1314
DAEMONS = ("dae", "daed")


class InstallDaedeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((SCRIPTS / "install_daede.py").is_file(), "Installer is not implemented")
        self.installer = importlib.import_module("install_daede")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tree = self.root / "wrt"
        self.downloaded = self.root / "downloaded"
        self.feeds = {name: self.tree / "feeds/packages/net" / name for name in DAEMONS}
        self.links = {name: self.tree / "package/feeds/packages" / name for name in DAEMONS}
        self.group = self.tree / "package/custom/kenzok8_openwrt-daede"
        for name in DAEMONS:
            self.write(self.feeds[name] / "Makefile", f"original {name} feed recipe\n")
        self.write(self.downloaded / "daed/Makefile", "maintained daemon recipe\n")
        self.write(self.downloaded / "daed/patches/001-fix.patch", "full patch contents\n")
        self.write(self.downloaded / "daed/files/daed.init", "service configuration\n")
        self.write(self.downloaded / "luci-app-daede/Makefile", ANCHOR + "\ninclude package.mk\n")
        self.write(self.downloaded / "luci-app-daede/root/usr/share/daede/view", "LuCI resource\n")
        self.write(self.downloaded / "dae/files/dae.config", "config dae 'config'\n")
        self.write(self.downloaded / "dae/Makefile", "maintained DAE recipe\n")
        self.write(self.downloaded / "dae/files/dae.init", "DAE init contents\n")
        self.write(self.downloaded / "dae/patches/001-fix.patch", "DAE patch contents\n")
        self.write(self.downloaded / "upgrade.sh", "unwanted upgrade script\n")
        for recipe in ("dae", "daed", "luci-app-daede"):
            shutil.copytree(SERVICE_FIXTURES / recipe, self.downloaded / recipe, dirs_exist_ok=True)

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))

    def symlink(self, name, *, target=None):
        link = self.links[name]
        target = self.feeds[name] if target is None else target
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(os.path.relpath(target, link.parent), target_is_directory=True)
        except OSError as error:
            if getattr(error, "winerror", None) != WINDOWS_SYMLINK_PRIVILEGE_ERROR:
                raise
            self.skipTest("Windows lacks real symlink privilege; Linux CI must execute this test")

    def create_links(self):
        for name in DAEMONS:
            self.symlink(name)

    def test_both_feed_links_are_replaced_and_original_sources_preserved(self):
        self.create_links()
        record = self.installer.install_daede(self.tree, self.downloaded, SOURCE)
        for name in DAEMONS:
            self.assertFalse(self.links[name].is_symlink())
            self.assertFalse(self.links[name].exists())
            self.assertEqual((self.feeds[name] / "Makefile").read_text(), f"original {name} feed recipe\n")
        self.assertEqual((self.group / "daed/Makefile").read_text(), "maintained daemon recipe\n")
        self.assertEqual((self.group / "dae/Makefile").read_text(), "maintained DAE recipe\n")
        self.assertEqual(record["repo"], SOURCE["repo"])
        self.assertEqual(record["sha"], SOURCE["sha"])
        removed = {item["removed_symlink"] for item in record["replacements"]}
        preserved = {item["preserved_feed"] for item in record["replacements"]}
        self.assertEqual(removed, {"package/feeds/packages/dae", "package/feeds/packages/daed"})
        self.assertEqual(preserved, {"feeds/packages/net/dae", "feeds/packages/net/daed"})
        dependencies = [item["added"] for item in record["adaptations"] if "added" in item]
        self.assertEqual(dependencies, [HOST_DEPENDENCY])

    def test_either_wrong_link_preserves_both_links(self):
        wrong = self.tree / "feeds/packages/net/another-daemon"
        self.write(wrong / "Makefile", "preserve unrelated feed\n")
        for name in DAEMONS:
            with self.subTest(name=name):
                self.create_links()
                self.links[name].unlink()
                self.symlink(name, target=wrong)
                with self.assertRaisesRegex(ValueError, "Unexpected .* link target"):
                    self.installer.install_daede(self.tree, self.downloaded, SOURCE)
                self.assertTrue(all(link.is_symlink() for link in self.links.values()))
                self.assertEqual(self.links[name].resolve(), wrong.resolve())
                self.assertFalse(self.group.exists())
                for link in self.links.values():
                    link.unlink()

    def test_either_missing_link_preserves_the_other_link(self):
        for missing in DAEMONS:
            with self.subTest(missing=missing):
                retained = "daed" if missing == "dae" else "dae"
                self.symlink(retained)
                with self.assertRaisesRegex(ValueError, "symbolic link"):
                    self.installer.install_daede(self.tree, self.downloaded, SOURCE)
                self.assertTrue(self.links[retained].is_symlink())
                self.assertFalse(self.links[missing].exists())
                self.assertFalse(self.group.exists())
                self.links[retained].unlink()

    def test_payload_error_preserves_both_feed_links(self):
        self.create_links()
        (self.downloaded / "dae/Makefile").unlink()
        with self.assertRaisesRegex(ValueError, "Missing source file"):
            self.installer.install_daede(self.tree, self.downloaded, SOURCE)
        self.assertTrue(all(link.is_symlink() for link in self.links.values()))
        self.assertFalse(self.group.exists())

    def test_real_directory_is_rejected_and_retained(self):
        for name in DAEMONS:
            with self.subTest(name=name):
                self.write(self.links[name] / "user-file", "must remain\n")
                with self.assertRaisesRegex(ValueError, "symbolic link"):
                    self.installer.validate_feed_link(self.tree, name)
                self.assertEqual((self.links[name] / "user-file").read_text(), "must remain\n")
                self.assertFalse(self.group.exists())

    def test_missing_feed_link_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            self.installer.install_daede(self.tree, self.downloaded, SOURCE)
        self.assertFalse(self.group.exists())

    def test_full_daed_and_luci_payload_is_copied(self):
        self.installer.install_payload(self.downloaded, self.group)
        self.assertEqual((self.group / "daed/patches/001-fix.patch").read_text(), "full patch contents\n")
        self.assertIn('procd_set_param command /usr/share/luci-app-daede/backend-exec "$CONF" "$PROG" run',
                      (self.group / "daed/files/daed.init").read_text(encoding="utf-8"))
        resource = self.group / "luci-app-daede/root/usr/share/daede/view"
        self.assertEqual(resource.read_text(), "LuCI resource\n")

    def test_complete_dae_recipe_includes_config_init_and_patches(self):
        self.installer.install_payload(self.downloaded, self.group)
        copied = sorted(path.relative_to(self.group / "dae").as_posix()
                        for path in (self.group / "dae").rglob("*") if path.is_file())
        self.assertEqual(copied, ["Makefile", "files/dae.config", "files/dae.init", "patches/001-fix.patch"])
        self.assertEqual((self.group / "dae/Makefile").read_text(), "maintained DAE recipe\n")
        self.assertEqual((self.group / "dae/files/dae.config").read_text(), "config dae 'config'\n")
        self.assertIn('procd_set_param command /usr/share/luci-app-daede/backend-exec "$CONF" "$PROG" run',
                      (self.group / "dae/files/dae.init").read_text(encoding="utf-8"))
        self.assertEqual((self.group / "dae/patches/001-fix.patch").read_text(), "DAE patch contents\n")
        self.assertFalse((self.group / "upgrade.sh").exists())

    def test_service_exclusion_is_applied_and_recorded_after_copy(self):
        records = self.installer.install_payload(self.downloaded, self.group)
        for name in DAEMONS:
            relative = Path(name) / "files" / f"{name}.init"
            self.assertIn("backend_start_allowed", (self.group / relative).read_text(encoding="utf-8"))
            self.assertEqual((self.downloaded / relative).read_bytes(),
                             (SERVICE_FIXTURES / relative).read_bytes())
        patches = [record["patch"] for record in records if "patch" in record]
        self.assertEqual(patches, ["003-daede-backend-exclusion.patch"])

    def test_host_dependency_is_added_only_to_the_copied_luci_recipe(self):
        recipe = self.downloaded / "luci-app-daede/Makefile"
        original = recipe.read_bytes()
        adaptations = self.installer.install_payload(self.downloaded, self.group)
        installed = (self.group / "luci-app-daede/Makefile").read_text(encoding="utf-8")
        self.assertEqual(installed.splitlines().count(HOST_DEPENDENCY), 1)
        self.assertIn("DEPENDS:=+luci-base +flock ", installed)
        self.assertIn("$(INSTALL_BIN) ./root/usr/share/luci-app-daede/backend-exec "
                      "$(1)/usr/share/luci-app-daede/backend-exec", installed)
        self.assertEqual(recipe.read_bytes(), original)
        dependencies = [item["added"] for item in adaptations if "added" in item]
        self.assertEqual(dependencies, [HOST_DEPENDENCY])

    def test_existing_custom_directory_is_not_overwritten(self):
        self.write(self.group / "keep", "previous work\n")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.installer.install_payload(self.downloaded, self.group)
        self.assertEqual((self.group / "keep").read_text(), "previous work\n")

    def test_host_dependency_anchor_does_not_rewrite_comment_text(self):
        comment = "# Example: " + ANCHOR + "\n"
        recipe = self.downloaded / "luci-app-daede/Makefile"
        self.write(recipe, comment + ANCHOR + "\n")
        adapted = self.installer.adapted_luci_recipe(recipe)
        expected = comment + ANCHOR + "\n" + HOST_DEPENDENCY + "\n"
        self.assertEqual(adapted.decode("utf-8"), expected)
        self.assertEqual(recipe.read_text(encoding="utf-8"), comment + ANCHOR + "\n")

    def test_missing_source_file_fails_before_copying(self):
        for name in ("dae/Makefile", "daed/Makefile", "luci-app-daede/Makefile", "dae/files/dae.config"):
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
                    self.installer.adapted_luci_recipe(self.downloaded / "luci-app-daede/Makefile")
                self.assertFalse(self.group.exists())

    def test_existing_host_dependency_is_not_silently_duplicated(self):
        self.write(self.downloaded / "luci-app-daede/Makefile", ANCHOR + "\n" + HOST_DEPENDENCY)
        with self.assertRaisesRegex(ValueError, "already declares PKG_BUILD_DEPENDS"):
            self.installer.adapted_luci_recipe(self.downloaded / "luci-app-daede/Makefile")
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
