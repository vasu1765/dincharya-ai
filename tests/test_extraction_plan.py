import ast
import hashlib
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import source_sync as sync
spec=importlib.util.spec_from_file_location('extraction_plan',ROOT/'scripts/plan-version-extraction.py')
planner=importlib.util.module_from_spec(spec);spec.loader.exec_module(planner)


class ExtractionPlanTests(unittest.TestCase):
    def toc(self):
        rows=[]
        for i,table in enumerate(('workflow_history','workflow_publish_history','workflow_published_version')):
            rows.extend([f'{i*2+1}; 1259 1 TABLE public {table} synthetic_owner',
                         f'{i*2+2}; 0 1 TABLE DATA public {table} synthetic_owner'])
        rows.append('99; 0 2 TABLE DATA public credentials_entity synthetic_owner')
        return '\n'.join(rows)

    def test_list_contains_exact_six_entries_not_unapproved_rows(self):
        selected,entries=planner.selected_list(self.toc())
        self.assertEqual(len(selected.splitlines()),6)
        self.assertEqual(len(entries),6)
        self.assertNotIn(b'credentials_entity',selected)

    def test_duplicate_id_even_in_unapproved_entry_rejects(self):
        toc=self.toc()+'\n1; 0 2 TABLE DATA public execution_entity synthetic_owner\n'
        with self.assertRaises(sync.Rejected):planner.selected_list(toc)

    def test_archive_regular_exact_checksum_and_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'n8n.dump';manifest=root/'SHA256SUMS'
            archive.write_bytes(b'synthetic archive placeholder, not a PostgreSQL dump')
            expected=hashlib.sha256(archive.read_bytes()).hexdigest()
            manifest.write_text(expected+'  ./n8n.dump\n')
            self.assertEqual(planner.verify_archive(archive,manifest),expected)
            archive.write_bytes(b'changed synthetic bytes')
            with self.assertRaises(sync.Rejected):planner.verify_archive(archive,manifest)

    def test_ambiguous_checksum_entry_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'n8n.dump';archive.write_bytes(b'synthetic')
            manifest=root/'SHA256SUMS';manifest.write_text(('a'*64+'  n8n.dump\n')*2)
            with self.assertRaises(sync.Rejected):planner.verify_archive(archive,manifest)

    def test_generated_shell_syntax_and_network_isolation(self):
        script=planner.administrator_script('/tmp/synthetic backup/n8n.dump','/tmp/synthetic plan',ROOT/'scripts/plan-version-extraction.py','postgres:17')
        subprocess.run(['bash','-n'],input=script,check=True,capture_output=True)
        for required in (b'--network=none',b'--pull=never',b'--read-only',b'--cap-drop=ALL',b'--entrypoint pg_restore',b'--use-list=/input/authorized.list',b'--file=-',b'verify-toc',b'set -C'):
            self.assertIn(required,script)
        for forbidden in (b'docker exec',b'--dbname=',b'--create ',b'docker compose',b'--privileged'):
            self.assertNotIn(forbidden,script)

    def test_recorded_client_version_check_accepts_exact_version(self):
        script=planner.administrator_script('/tmp/backup/n8n.dump','/tmp/plan',ROOT/'scripts/plan-version-extraction.py','postgres:17').decode()
        line=next(line for line in script.splitlines() if 're.fullmatch' in line)
        source=shlex.split(line)[-1]
        parsed=ast.parse(source)
        pattern=next(node.value for node in ast.walk(parsed) if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('pg_restore'))
        import re
        self.assertIsNotNone(re.fullmatch(pattern,'pg_restore (PostgreSQL) 17.11\n'))
        self.assertIsNone(re.fullmatch(pattern,'pg_restore (PostgreSQL) 16.9\n'))

    def test_mount_delimiters_and_image_command_injection_reject(self):
        for image in ('postgres:17;synthetic','postgres:17\nsynthetic'):
            with self.assertRaises(sync.Rejected):planner.administrator_script('/tmp/b/n8n.dump','/tmp/o',__file__,image)
        with self.assertRaises(sync.Rejected):planner.administrator_script('/tmp/with,comma/n8n.dump','/tmp/o',__file__,'postgres:17')

    def test_generated_script_end_to_end_uses_fake_docker_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'output';out.mkdir(mode=0o700)
            archive=root/'n8n.dump';archive.write_bytes(b'synthetic archive bytes')
            expected=hashlib.sha256(archive.read_bytes()).hexdigest()
            (root/'SHA256SUMS').write_text(expected+'  ./n8n.dump\n')
            selected,_=planner.selected_list(self.toc())
            (out/'authorized.list').write_bytes(selected)
            (out/'archive-sha256.private.txt').write_text(expected+'\n')
            fakebin=root/'fakebin';fakebin.mkdir()
            fake=fakebin/'docker'
            fake.write_text('#!/usr/bin/env python3\nimport sys,os\nfrom pathlib import Path\na=sys.argv[1:]\n'
                'if a[:2]==["image","inspect"]: print("sha256:"+"a"*64)\n'
                'elif "--version" in a: print("pg_restore (PostgreSQL) 17.11")\n'
                'elif "--list" in a: print(Path(os.environ["SYNTHETIC_TOC_PATH"]).read_text())\n'
                'else:\n'
                ' assert "--network=none" in a and "--use-list=/input/authorized.list" in a\n'
                ' print("-- synthetic selected SQL, never executed")\n')
            fake.chmod(0o700)
            toc=root/'toc.txt';toc.write_text(self.toc())
            shell=planner.administrator_script(archive,out,ROOT/'scripts/plan-version-extraction.py','postgres:17')
            script=out/'extract.sh';script.write_bytes(shell)
            env=dict(PATH=str(fakebin)+os.pathsep+os.defpath,
                     SYNTHETIC_TOC_PATH=str(toc),PYTHONDONTWRITEBYTECODE='1')
            subprocess.run(['bash',str(script)],env=env,check=True,capture_output=True)
            self.assertTrue((out/'EXTRACTED').is_file())
            self.assertTrue((out/'authorized-tables.sql').is_file())
            self.assertFalse((out/'authorized-tables.sql.partial').exists())
            self.assertEqual((out/'authorized-tables.sql').stat().st_mode & 0o777,0o600)

    def test_scheduler_source_export_is_bounded_and_never_starts_n8n(self):
        script=(ROOT/'scripts/export-scheduler-source.sh').read_bytes()
        subprocess.run(['bash','-n'],input=script,check=True,capture_output=True)
        for required in (b'--network=none',b'--read-only',b'--pull=never',b'--entrypoint /bin/sh',
                         b'dist/nodes/Schedule',b'node_modules/n8n-nodes-base/package.json',b'= 2.47.3'):
            self.assertIn(required,script)
        for forbidden in (b'docker exec ',b'docker compose ',b'--mount ',b'--env-file',b'--privileged'):
            self.assertNotIn(forbidden,script)

    def test_scheduler_source_export_with_fake_docker_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fakebin=root/'fakebin';fakebin.mkdir()
            fake=fakebin/'docker'
            fake.write_text('#!/usr/bin/env python3\nimport sys\na=sys.argv[1:]\n'
                'if a[:2]==["image","inspect"]: print("sha256:6723b440354b"+"a"*52)\n'
                'else:\n'
                ' assert "--network=none" in a and "--entrypoint" in a and "/bin/sh" in a\n'
                ' assert not any(x.startswith("--mount") or x=="--env-file" for x in a)\n'
                ' print("synthetic source archive placeholder, not an actual tar")\n')
            fake.chmod(0o700)
            env={'PATH':str(fakebin)+os.pathsep+os.defpath,'SCHEDULER_SOURCE_ROOT':str(root),'PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(['bash',str(ROOT/'scripts/export-scheduler-source.sh')],env=env,check=True,capture_output=True)
            outputs=list(root.glob('n8n-scheduler-2.47.3-*'))
            self.assertEqual(len(outputs),1)
            self.assertTrue((outputs[0]/'EXPORTED').is_file())
            self.assertEqual((outputs[0]/'scheduler-source.tar').stat().st_mode&0o777,0o600)


if __name__=='__main__':unittest.main()
