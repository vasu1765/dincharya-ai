"""Execute the two Acer astronomy suites and reject missing or skipped tests."""
from pathlib import Path
import os
import sys
import unittest

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
if not Path(os.environ['DINCHARYA_PUBLIC_DE440S']).is_file():
    sys.exit('Pinned public kernel required')
for pattern, expected in [('test_recurring.py', 4), ('test_historical_panchang.py', 9)]:
    suite = unittest.TestLoader().discover(str(root / 'tests'), pattern=pattern)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.testsRun != expected or result.skipped or not result.wasSuccessful():
        sys.exit('Required astronomy suite incomplete')
