"""Exercise the actual backup script with fake external tools and a temporary repo."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


class BackupMarkerTests(unittest.TestCase):
    def test_only_successful_upload_publishes_or_replaces_marker(self):
        script = Path(__file__).resolve().parents[3] / 'backup.sh'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bindir = root / 'bin'
            bindir.mkdir()
            fake = '''#!/usr/bin/env python3
import os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
if name == 'docker':
    print('synthetic database dump')
elif name == 'tar':
    Path(sys.argv[sys.argv.index('--file') + 1]).write_bytes(b'synthetic archive')
elif name == 'gpg':
    Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(b'synthetic encrypted archive')
elif name == 'aws':
    sys.exit(int(os.environ.get('SYNTHETIC_UPLOAD_FAILURE', '0')))
'''
            for name in ('docker', 'tar', 'gpg', 'aws'):
                path = bindir / name
                path.write_text(fake)
                path.chmod(0o755)
            (root / '.env').write_text('\n'.join(key + '=synthetic-test-value' for key in
                ('PAPERLESS_DB_ROOT_PASSWORD', 'SHLINK_DB_ROOT_PASSWORD', 'IMMICH_DB_PASSWORD',
                 'IMMICH_DB_USERNAME', 'IMMICH_DB_DATABASE_NAME')) + '\n')
            (root / 'passphrase').write_text('synthetic-test-value')
            (root / 'backup.env').write_text("S3_BUCKET=s3://synthetic-test-bucket\nGPG_PASSPHRASE_FILE='" + str(root / 'passphrase') + "'\n")
            env = {'PATH': str(bindir) + ':' + os.environ['PATH'], 'HOMELAB_ROOT': str(root),
                   'BACKUP_CONFIG': str(root / 'backup.env'), 'BACKUP_WORK_DIR': str(root)}
            marker = root / 'data/asterisk-status/last-backup-success'
            failed = subprocess.run(['bash', str(script)], env={**env, 'SYNTHETIC_UPLOAD_FAILURE': '1'},
                                    capture_output=True, timeout=15)
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(marker.exists())
            succeeded = subprocess.run(['bash', str(script)], env=env, capture_output=True, timeout=15)
            self.assertEqual(succeeded.returncode, 0, succeeded.stderr.decode())
            self.assertLess(abs(time.time() - int(marker.read_text())), 10)
            marker.write_text('100')
            subprocess.run(['bash', str(script)], env={**env, 'SYNTHETIC_UPLOAD_FAILURE': '1'},
                           capture_output=True, timeout=15)
            self.assertEqual(marker.read_text(), '100')
