import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.operations.session import main
from dincharya.attended_runtime import PG,APP,N8N,KERNEL_SHA


class SessionToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state=Path(self.tmp.name)
        self.session=self.state/"session"
        self.session.mkdir(mode=0o700)
        (self.session/"STOP").touch()
        self.sha="1"*40
        for k,v in {"revision":self.sha,"pg":"2"*64,"app":"3"*64,"relay":"4"*64}.items():
            (self.state/k).write_text(v)
            (self.state/k).chmod(0o600)
        self.input=self.state/"input"
        self.input.write_text(json.dumps(dict(sha=self.sha,host="44c1ef83-c50e-4ecc-8f19-4b112bc40f29",
            app=APP,pg=PG,n8n=N8N,kernel_sha256=KERNEL_SHA,owner=901,bot=902,bot_username="FixtureBot",
            start=1795564800,end=1795568400,silent="Schedule Quiet on 2026-11-25 at 05:40",
            reminder="Schedule Study on 2026-11-25 at 05:50",question="What was the tithi on 2023-12-06?",profile="laptop-beta")))
        self.input.chmod(0o600)
        template=json.loads(self.input.read_bytes())
        template.update(owner=93001,bot=93002)
        (self.session/"manifest.json").write_text(json.dumps(template))
        (self.session/"manifest.json").chmod(0o600)
        self.digest=hashlib.sha256(self.input.read_bytes()).hexdigest()
        patcher=patch("subprocess.check_output",return_value=self.sha+"\n")
        patcher.start()
        self.addCleanup(patcher.stop)

    def runop(self,op,*args):
        return main([op,str(self.state),*map(str,args)])

    def test_recreate_and_bind_workflow(self):
        self.runop("prepare","--input",self.input)
        with self.assertRaises(ValueError):
            self.runop("approve","--owner-approved-digest","f"*64)
        self.runop("approve","--owner-approved-digest",self.digest)
        with self.assertRaises(FileExistsError):
            self.runop("approve","--owner-approved-digest",self.digest)
        with patch.dict(os.environ),patch("os.execvp") as launch:
            self.runop("start")
            launch.assert_called_once_with("bash",["bash","scripts/laptop_beta.sh","start",str(self.state)])
        (self.state/"app").write_text("9"*64)
        with self.assertRaises(ValueError):
            self.runop("start")

    def test_unsafe_input_and_unfenced_prepare(self):
        self.input.chmod(0o644)
        with self.assertRaises(ValueError):
            self.runop("prepare","--input",self.input)
        (self.session/"STOP").unlink()
        with self.assertRaises(ValueError):
            self.runop("prepare","--input",self.input)

    def test_unapproved_start_refused_and_stop_sets_fence_first(self):
        self.runop("prepare","--input",self.input)
        with self.assertRaises(FileNotFoundError):
            self.runop("start")
        (self.session/"STOP").unlink()
        with patch("os.execvp") as stop:
            self.runop("stop")
            self.assertTrue((self.session/"STOP").is_file())
            stop.assert_called_once()

    def test_consumed_or_prepared_stage_never_overwritten(self):
        self.runop("prepare","--input",self.input)
        before=(self.session/"manifest.json").read_bytes()
        with self.assertRaises(ValueError):
            self.runop("prepare","--input",self.input)
        self.assertEqual(before,(self.session/"manifest.json").read_bytes())

    def test_minimal_private_input_preserves_reviewed_pins(self):
        full=json.loads(self.input.read_bytes())
        keys=("owner","bot","bot_username","silent","reminder","start","end","question")
        self.input.write_text(json.dumps({k:full[k] for k in keys}))
        self.runop("prepare","--input",self.input)
        self.assertEqual(json.loads((self.session/"manifest.json").read_bytes()),full)
