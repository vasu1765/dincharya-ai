from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest

from physical import validate_monitor,phase_guard


class PhysicalCheckpoints(unittest.TestCase):
    def samples(self):
        return [dict(utc=datetime.fromtimestamp(t,timezone.utc).isoformat(),
                     state='outage' if 1845<=t<1935 else 'ready') for t in range(0,2011,15)]

    def check(self,rows):
        validate_monitor(rows,15,1815,1830,1935)

    def test_external_monitor_full_lid_and_recovery(self):
        self.check(self.samples())
        for change in ('gap','sleep','no_outage','no_recovery'):
            rows=self.samples()
            if change=='gap':
                del rows[10:13]
            if change=='sleep':
                rows[15]['state']='miss'
            if change=='no_outage':
                for row in rows:
                    row['state']='ready'
            if change=='no_recovery':
                for row in rows[129:]:
                    row['state']='outage'
            with self.subTest(change=change),self.assertRaises(RuntimeError):
                self.check(rows)
    def test_phase_reservation_survives_interruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            with self.assertRaises(RuntimeError):
                phase_guard(path,'arm')
            phase_guard(path,'prepare')
            with self.assertRaises(FileExistsError):
                phase_guard(path,'prepare')
            (path/'prepare.done').touch()
            phase_guard(path,'arm')
            with self.assertRaises(FileExistsError):
                phase_guard(path,'arm')
