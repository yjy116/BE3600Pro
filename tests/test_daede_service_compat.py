"""Exercise patched upstream service/UI code; external router calls are harnessed."""

import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/daede"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
TIMEOUT_SECONDS = 20
SHELL = shutil.which("bash") or "C:/Program Files/Git/bin/bash.exe"
NODE = shutil.which("node")
WIDGETS = "luci-app-daede/htdocs/luci-static/resources/view/daede/widgets.js"
BACKEND = "luci-app-daede/htdocs/luci-static/resources/view/daede/backend.js"


class DaedeServiceCompatTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((SCRIPTS / "daede_service_compat.py").is_file(), "Compatibility adapter missing")
        self.compat = importlib.import_module("daede_service_compat")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.bundle = Path(self.temporary.name) / "bundle"
        shutil.copytree(FIXTURES, self.bundle)

    def adapt(self):
        return self.compat.adapt_services(self.bundle)

    def shell(self, backend, scenario):
        code = (self.bundle / f"{backend}/files/{backend}.init").read_text(encoding="utf-8")
        code = code.replace('. /usr/share/daed/cleanup.sh', ': # harness excludes external cleanup library')
        harness = """
extra_command() { :; }
logger() { :; }
uci() { [ "$ACTIVE" != missing ] || return 1; printf '%s\n' "$ACTIVE"; }
pidof() { return "$OTHER_STATUS"; }
config_load() { :; }
config_get_bool() { eval "$1=1"; }
rm() { echo UNSAFE_RM; }
ip() { echo UNSAFE_IP; }
"""
        result = subprocess.run([SHELL, "-c", harness + code + scenario],
                                capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
        return result

    def node(self, scenario):
        widgets = (self.bundle / WIDGETS).read_text(encoding="utf-8").split("return baseclass.extend({")[0]
        backend = (self.bundle / BACKEND).read_text(encoding="utf-8").split("return baseclass.extend({")[0]
        harness = """
const events = [], state = { dae: true, daed: false };
const persisted = { dae: 1, daed: 1 };
let failStop = false, leaveRunning = false, failCommit = false;
let noResult = false, pidofCode = 1, rpcFails = false;
let snapshots = [{}];
const fs = {exec: async (command, args) => {
  events.push([command, ...args]);
  if (noResult) return undefined;
  if (command === '/bin/pidof') {
    if (rpcFails) throw Error('RPC denied');
    return {code: pidofCode};
  }
  if (command === '/sbin/uci') {
    if (args[0] === 'set' && args[1].includes('.enabled=')) {
      persisted[args[1].split('.')[0]] = Number(args[1].split('=')[1]);
    }
    return {code: failCommit && args[0] === 'commit' ? 1 : 0, stderr: 'uci failed'};
  }
  if (args[0] === 'stop') {
    if (failStop) return {code: 1, stderr: 'stop rejected'};
    if (!leaveRunning) state[command.split('/').pop()] = false;
  }
  return {code: 0};
}, stat: async () => ({}), write: async () => {}};
const uci = {set: () => {}, get: () => 'dae'};
const L = {resolveDefault: (value, fallback) => Promise.resolve(value).catch(() => fallback)};
String.prototype.format = function(...args) { let n=0; return this.replace(/%s/g, () => args[n++]); };
const translate = value => value;
const backend = {
  BACKENDS: {dae: {name:'dae',uci:'dae',initd:'/etc/init.d/dae'},
             daed: {name:'daed',uci:'daed',initd:'/etc/init.d/daed'}},
  detectRunning: async () => ({...state}),
  serviceStatus: async () => ({running: false})
};
"""
        exports = "return {stopBackends, toggleService};"
        program = harness + "const ui = new Function('fs','backend','_', " + json.dumps(widgets + exports) + ")(fs,backend,translate);\n"
        exports = "return {setActiveBackend, detectRunning, serviceStatus};"
        rpc = "{declare:()=>async()=>{if(rpcFails)throw Error('RPC denied'); return snapshots.length>1?snapshots.shift():snapshots[0];}}"
        program += "const cfg = new Function('fs','uci','L','rpc', " + json.dumps(backend + exports) + ")(fs,uci,L," + rpc + ");\n"
        program += "(async()=>{" + scenario + "})().catch(e=>{console.error(e);process.exit(1)});"
        return subprocess.run([NODE, "-e", program], capture_output=True, text=True,
                              timeout=TIMEOUT_SECONDS)

    def test_pinned_patch_applies_and_records_all_files(self):
        records = self.adapt()
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0]["files"]), 8)
        self.assertEqual(len(records[0]["sha256"]), 64)
        self.assertIn("backend_start_allowed", (self.bundle / "dae/files/dae.init").read_text(encoding="utf-8"))

    def test_changed_upstream_is_rejected_before_any_write(self):
        init = self.bundle / "daed/files/daed.init"
        init.write_text(init.read_text(encoding="utf-8").replace('START=99', 'START=98'), encoding="utf-8")
        before = {path: path.read_bytes() for path in self.bundle.rglob("*") if path.is_file()}
        with self.assertRaisesRegex(ValueError, "upstream|fingerprint"):
            self.adapt()
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_double_application_is_explicitly_rejected(self):
        self.adapt()
        with self.assertRaisesRegex(ValueError, "upstream|fingerprint"):
            self.adapt()

    def test_boot_rejects_enabled_but_inactive_backend(self):
        self.adapt()
        for backend, active in (("dae", "daed"), ("daed", "dae")):
            with self.subTest(backend=backend):
                result = self.shell(backend, f'\nACTIVE={active}; OTHER_STATUS=1; start_service\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("active backend", result.stderr)
                self.assertNotIn("UNSAFE_", result.stdout)

    def test_start_gate_rejects_live_other_backend_and_bad_state(self):
        self.adapt()
        for backend in ("dae", "daed"):
            for active, status in ((backend, 0), (backend, 2), ("unknown", 1), ("missing", 1)):
                with self.subTest(backend=backend, active=active, status=status):
                    command = f'\nACTIVE={active}; OTHER_STATUS={status}; backend_start_allowed other\n'
                    result = self.shell(backend, command)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(result.stderr.strip())

    def test_selected_backend_can_pass_gate_after_other_has_exited(self):
        self.adapt()
        for backend in ("dae", "daed"):
            result = self.shell(backend, f'\nACTIVE={backend}; OTHER_STATUS=1; backend_start_allowed other\n')
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_stopping_idle_dae_preserves_live_daed_network(self):
        self.adapt()
        result = self.shell("dae", '\nACTIVE=daed; OTHER_STATUS=0; stop_service\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("leaving shared network", result.stderr)
        self.assertNotIn("UNSAFE_", result.stdout)

    def test_switch_disables_both_before_stop_and_then_changes_selection(self):
        self.adapt()
        result = self.node("""
await ui.stopBackends({dae:true, daed:true});
await cfg.setActiveBackend('daed');
if (persisted.dae !== 0 || persisted.daed !== 0 || state.dae) throw Error('old state retained');
const stop = events.findIndex(e=>e[1]==='stop');
const active = events.findIndex(e=>String(e[2]).includes('active_backend='));
if (stop < 0 || active <= stop || events.filter(e=>e[1]==='disable').length !== 2) throw Error('unsafe order');
if (events.filter(e=>e[1]==='stop').length !== 2) throw Error('pending/idle backend not stopped');
""")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_stop_failure_or_surviving_process_prevents_selection_change(self):
        self.adapt()
        for failure in ("failStop=true", "leaveRunning=true"):
            result = self.node(failure + ";" + """
let rejected = false;
try { await ui.stopBackends({dae:true,daed:true}); await cfg.setActiveBackend('daed'); }
catch (e) { rejected = true; }
if (!rejected || events.some(e=>String(e[2]).includes('active_backend='))) throw Error('unsafe switch');
""")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_uci_commit_failure_is_exposed(self):
        self.adapt()
        result = self.node("""
failCommit = true;
let rejected = false;
try { await cfg.setActiveBackend('daed'); } catch (e) { rejected = /uci failed/.test(e.message); }
if (!rejected) throw Error('commit failure swallowed');
""")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pidof_rc1_is_stopped_but_errors_are_not_stopped(self):
        self.adapt()
        result = self.node("""
const stopped = await cfg.detectRunning();
if (stopped.dae || stopped.daed) throw Error('pidof rc 1 is not stopped');
for (const mode of ['code', 'missing', 'rpc']) {
  pidofCode = mode === 'code' ? 2 : 1;
  noResult = mode === 'missing'; rpcFails = mode === 'rpc';
  let rejected = false;
  try { await cfg.detectRunning(); } catch(e) { rejected = true; }
  if (!rejected) throw Error('probe error treated as stopped: ' + mode);
}
""")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_procd_guard_tail_is_awaited_and_rpc_failures_block_switch(self):
        self.adapt()
        result = self.node("""
backend.serviceStatus = cfg.serviceStatus;
state.dae = false;
snapshots = [{daed:{instances:{daed:{running:true,pid:42}}}}, {}];
await ui.stopBackends({daed:true});
if (snapshots.length !== 1) throw Error('guard cleanup not awaited');
rpcFails = true;
let rejected = false;
try { await ui.stopBackends({daed:true}); } catch(e) { rejected = /RPC denied/.test(e.message); }
if (!rejected) throw Error('service list failure swallowed');
""")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_exec_response_cannot_change_selection(self):
        self.adapt()
        result = self.node("""
noResult = true;
let rejected = false;
try { await ui.stopBackends({dae:true,daed:true}); await cfg.setActiveBackend('daed'); }
catch(e) { rejected = true; }
if (!rejected || events.some(e=>String(e[2]).includes('active_backend='))) throw Error('missing result accepted');
""")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_guard_probe_has_precise_acl_and_helper_is_installed(self):
        self.adapt()
        acl = self.bundle / 'luci-app-daede/root/usr/share/rpcd/acl.d/luci-app-daede.json'
        access = json.loads(acl.read_text(encoding='utf-8'))['luci-app-daede']['read']['file']
        self.assertEqual(access['/bin/pidof daed daed-guard'], ['exec'])
        self.assertFalse(any('backend-exec' in command for command in access))
        recipe = (self.bundle / 'luci-app-daede/Makefile').read_text(encoding='utf-8')
        self.assertIn('+flock ', recipe)
        self.assertIn('$(INSTALL_BIN) ./root/usr/share/luci-app-daede/backend-exec', recipe)


if __name__ == "__main__":
    unittest.main()
