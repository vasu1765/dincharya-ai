import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import source_sync as sync
import scheduler_source_evidence as source
from workflow_security import runtime_state_inventory


class SchedulerSourceEvidenceTests(unittest.TestCase):
    def files(self):
        # Synthetic structural source profile, never loaded as executable JS.
        node = '''const state = this.getWorkflowStaticData('node');
const enabled = (0, GenericFunctions_1.recurrenceCheck)(recurrence, staticData.recurrenceRules, timezone);
(0, GenericFunctions_1.resetStaleRecurrence)(staticData, rules);
this.helpers.registerCron(cron, callback);
const key = `${workflowId}:${nodeId}:${scheduledTime.toISOString()}`;
executeTrigger(recurrence, true);
'''
        helper = '''const previous = recurrenceRules[index] ?? undefined;
recurrenceRules[index] = absoluteMinute;
if (storedSignature === signature) return;
staticData.recurrenceRules[index] = undefined;
staticData.recurrenceRuleSignatures[index] = signature;
staticData.recurrenceRules.length = rules.length;
'''
        return {'package.json':sync.encoded({'name':'n8n','version':'2.47.3'}),
                'node_modules/n8n-nodes-base/package.json':sync.encoded({'name':'n8n-nodes-base','version':'2.47.2'}),
                source.PREFIX+'ScheduleTrigger.node.js':node.encode(),
                source.PREFIX+'GenericFunctions.js':helper.encode()}

    def export(self, root, files=None, extra=None):
        contents=self.files() if files is None else files
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w') as archive:
            for name,content in contents.items():
                member=tarfile.TarInfo(name);member.size=len(content)
                archive.addfile(member,io.BytesIO(content))
            if extra is not None:archive.addfile(extra)
        originals={'scheduler-source.tar':stream.getvalue(),
                   'image-id.private.txt':('sha256:6723b440354b'+'a'*52+'\n').encode(),
                   'verified-version.private.txt':b'2.47.3 (synthetic profile)\n'}
        for name,value in originals.items():(root/name).write_bytes(value)
        (root/'EXPORTED').write_bytes(b'STATIC_SOURCE_EXPORTED: synthetic fixture\n')
        (root/'SHA256SUMS').write_text(''.join(f'{sync.digest(value)}  {name}\n' for name,value in originals.items()))
        return originals

    def record(self):
        return {'nodes':[{'name':'Synthetic schedule','type':'n8n-nodes-base.scheduleTrigger','typeVersion':1.4}],
                'staticData':{'node:Synthetic schedule':{'recurrenceRules':[12345],'recurrenceRuleSignatures':['minutes:5']}}}

    def evidence(self):
        evidence=source.inspect_source_files(self.files());evidence['checksums_verified']=True
        return evidence

    def test_verified_source_profile_distinguishes_package_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            originals=self.export(Path(tmp))
            stored,evidence=source.read_verified_source_export(tmp)
            self.assertEqual(stored,originals)
            self.assertEqual(evidence['n8n_version'],'2.47.3')
            self.assertEqual(evidence['node_package_version'],'2.47.2')
            self.assertFalse(evidence['historical_runtime_compatibility_established'])
            self.assertFalse(evidence['import_api_contract_verified'])

    def test_native_state_classified_b_without_mutation_or_reset_approval(self):
        record=self.record();before=copy.deepcopy(record)
        result=source.assess_scheduler_state(record,self.evidence())
        self.assertTrue(all(entry['classification']=='B' for entry in result))
        self.assertTrue(all(not entry['reset_approved'] and not entry['import_treatment_approved'] for entry in result))
        self.assertEqual(record,before)
        self.assertTrue(all(entry['classification']=='C' for entry in runtime_state_inventory(record)))

    def test_application_state_and_unknown_native_keys_stay_c(self):
        record=self.record();record['staticData']['node:Synthetic schedule']['unknown']='synthetic'
        result=source.assess_scheduler_state(record,self.evidence())
        self.assertEqual([entry['classification'] for entry in result],['B','B','C'])
        record['nodes'][0]['type']='synthetic.application'
        self.assertTrue(all(entry['classification']=='C' for entry in source.assess_scheduler_state(record,self.evidence())))

    def test_evidence_and_owner_version_are_required(self):
        with self.assertRaises(sync.Rejected):source.assess_scheduler_state(self.record(),{})
        record=self.record();record['nodes'][0]['typeVersion']=99
        self.assertTrue(all(entry['classification']=='C' for entry in source.assess_scheduler_state(record,self.evidence())))

    def test_wrong_package_version_or_changed_implementation_rejected(self):
        files=self.files();files['package.json']=sync.encoded({'name':'n8n','version':'2.47.4'})
        with self.assertRaises(sync.Rejected):source.inspect_source_files(files)
        files=self.files();files[source.PREFIX+'GenericFunctions.js']=b'// unsupported source'
        with self.assertRaises(sync.Rejected):source.inspect_source_files(files)

    def test_corrupt_archive_checksum_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.export(root)
            (root/'scheduler-source.tar').write_bytes(b'corrupt synthetic source')
            with self.assertRaises(sync.Rejected):source.read_verified_source_export(root)

    def test_archive_symlinks_traversal_and_unapproved_paths_rejected(self):
        for name,kind in (('../escape',tarfile.REGTYPE),(source.PREFIX+'link',tarfile.SYMTYPE),('unrelated/private-file',tarfile.REGTYPE)):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                member=tarfile.TarInfo(name);member.type=kind;member.linkname='/synthetic-target'
                self.export(Path(tmp),extra=member)
                with self.assertRaises(sync.Rejected):source.read_verified_source_export(tmp)

    def test_known_native_state_still_rejected_by_conversion_gate(self):
        record=json.loads((ROOT/'tests/fixtures/workflow.raw.json').read_text())[0]
        record['staticData']={'global':{'synthetic':1}}
        with self.assertRaisesRegex(sync.Rejected,'RUNTIME_STATE_REQUIRES_REVIEW'):
            sync.convert_workflows(sync.encoded([record]),'raw','unknown')


if __name__=='__main__':unittest.main()
