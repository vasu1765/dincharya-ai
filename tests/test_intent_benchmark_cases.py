import json
import unittest

from intent_benchmark_cases import CASES, request, score


class BenchmarkProtocolTest(unittest.TestCase):
    def test_profiles_use_same_model_context_and_limits(self):
        for _, prompt, context, _ in CASES:
            original = request("original", "example", prompt, context)
            compact = request("compact", "example", prompt, context)
            self.assertEqual(original["options"], compact["options"])
            self.assertEqual(original["messages"][1], compact["messages"][1])
            self.assertTrue(original["format"]["additionalProperties"] is False)
            self.assertTrue(compact["format"]["additionalProperties"] is False)

    def test_failures_are_disjoint_and_compact_keeps_validator(self):
        expected = dict(kind="panchang", day="tomorrow")
        reply = json.dumps(expected)
        self.assertEqual(score("original", reply, expected), "shape")
        self.assertEqual(score("compact", reply, expected), "pass")
        self.assertEqual(score("compact", '{"kind":"clarify","kind":"panchang"}', expected), "json")
        self.assertEqual(score("compact", '{"kind":"civil_once","title":"A","day":"2027-02-31","clock":"09:00"}', expected),
                         "validator")
        self.assertEqual(score("compact", '{"kind":"panchang","day":"today"}', expected), "semantic")
        self.assertEqual(score("compact", '{"kind":"clarify","execute":true}', expected), "shape")
