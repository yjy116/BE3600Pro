"""Linux process tests: real flock/exec/signals, with router paths redirected to temp I/O."""

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from daede_service_compat import adapt_services, NEW_HELPER

TIMEOUT_SECONDS = 5
POLL_SECONDS = 0.02
SIGNAL_SETTLE_SECONDS = 0.1


@unittest.skipUnless(sys.platform.startswith('linux'), 'Requires real Linux flock/process signals')
class DaedeLockRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(shutil.which('flock'), 'util-linux flock is required')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        shutil.copytree(ROOT / 'tests/fixtures/daede', self.bundle)
        adapt_services(self.bundle)
        self.active = self.root / 'active'
        self.lock = self.root / 'backend.lock'
        self.dae = self.root / 'dae'
        self.guard = self.root / 'daed-guard'
        self.core = self.root / 'daed'
        self.helper = self.root / 'backend-exec'
        self.env = dict(os.environ, PATH=str(self.root) + ':' + os.environ['PATH'],
                        READY=str(self.root / 'ready'), RELEASE=str(self.root / 'release'))
        self.write_script(self.root / 'uci', '#!/bin/sh\ncat "' + str(self.active) + '"\n')
        helper = (self.bundle / NEW_HELPER).read_text(encoding='utf-8')
        helper = helper.replace('/usr/bin/dae', str(self.dae))
        helper = helper.replace(str(self.dae) + 'd-guard', str(self.guard))
        self.write_script(self.helper, helper.replace('/var/lock/daede-backend.lock', str(self.lock)))
        self.write_script(self.dae, '#!/bin/sh\nexit 0\n')
        self.write_script(self.core, '#!/bin/sh\nexit 0\n')

    def write_script(self, path, body):
        path.write_text(body, encoding='utf-8', newline='\n')
        path.chmod(0o755)

    def select(self, backend):
        self.active.write_text(backend + '\n', encoding='utf-8')

    def command(self, backend):
        return [str(self.helper), backend, str(self.dae if backend == 'dae' else self.guard), 'run']

    def run_backend(self, backend):
        return subprocess.run(self.command(backend), env=self.env, capture_output=True,
                              text=True, timeout=TIMEOUT_SECONDS)

    def start_backend(self, backend):
        process = subprocess.Popen(self.command(backend), env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.finish_process, process)
        return process

    def finish_process(self, process):
        (self.root / 'release').touch()
        try:
            process.communicate(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=TIMEOUT_SECONDS)

    def await_ready(self, process):
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if (self.root / 'ready').exists():
                return
            if process.poll() is not None:
                self.fail('Backend exited before readiness: ' + process.communicate()[1])
            time.sleep(POLL_SECONDS)
        self.fail('Backend readiness timed out')

    def make_guard(self):
        guard = (self.bundle / 'daed/files/daed-guard').read_text(encoding='utf-8')
        cleanup = '''
logger() { :; }
daed_cleanup_runtime() {
    [ "$DAED_GUARD_CLEANUP" = post-exit ] || return 0
    echo ready > "$READY"
    while [ ! -f "$RELEASE" ]; do sleep 0.02; done
    echo cleanup-complete
}
'''
        guard = guard.replace('. /usr/share/daed/cleanup.sh', cleanup)
        guard = guard.replace('/usr/bin/daed', str(self.core))
        guard = guard.replace('/proc/self/oom_score_adj', str(self.root / 'oom_score_adj'))
        self.write_script(self.guard, guard)

    def test_guard_cleanup_holds_lock_and_survives_repeated_stop(self):
        self.make_guard()
        self.select('daed')
        process = self.start_backend('daed')
        self.await_ready(process)
        self.select('dae')
        blocked = self.run_backend('dae')
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn('runtime lock', blocked.stderr)
        process.send_signal(signal.SIGTERM)
        process.send_signal(signal.SIGTERM)
        time.sleep(SIGNAL_SETTLE_SECONDS)
        self.assertIsNone(process.poll(), 'Repeated stop interrupted guard cleanup')
        (self.root / 'release').touch()
        output, error = process.communicate(timeout=TIMEOUT_SECONDS)
        self.assertEqual(process.returncode, 0, error)
        self.assertIn('cleanup-complete', output)
        result = self.run_backend('dae')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_execed_dae_keeps_lock_until_exit(self):
        self.write_script(self.dae, '''#!/bin/sh
echo ready > "$READY"
while [ ! -f "$RELEASE" ]; do sleep 0.02; done
''')
        self.write_script(self.guard, '#!/bin/sh\nexit 0\n')
        self.select('dae')
        process = self.start_backend('dae')
        self.await_ready(process)
        self.select('daed')
        result = self.run_backend('daed')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('runtime lock', result.stderr)
        (self.root / 'release').touch()
        process.communicate(timeout=TIMEOUT_SECONDS)
        self.assertEqual(process.returncode, 0)
        result = self.run_backend('daed')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_helper_rejects_wrong_selection_or_arbitrary_command(self):
        self.select('daed')
        result = self.run_backend('dae')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('active backend', result.stderr)
        result = subprocess.run([str(self.helper), 'dae', '/bin/true', 'run'],
                                env=self.env, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('invalid backend command', result.stderr)

    def test_stop_cleanup_releases_lock_before_restart_in_same_shell(self):
        code = (self.bundle / 'dae/files/dae.init').read_text(encoding='utf-8')
        code = code.replace('/var/lock/daede-backend.lock', str(self.lock))
        harness = '''
extra_command() { :; }
pidof() { return 1; }
rm() { :; }
ip() { return 1; }
umount() { :; }
'''
        command = harness + code + '\nstop_service\nflock -n "' + str(self.lock) + '" true\n'
        result = subprocess.run(['/bin/sh', '-c', command], capture_output=True, text=True,
                                timeout=TIMEOUT_SECONDS)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
