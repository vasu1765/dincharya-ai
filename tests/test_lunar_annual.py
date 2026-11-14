"""Cycle 3 scheduling boundaries without real transport or database access."""
from pathlib import Path
import unittest
from uuid import uuid4

from dincharya.lunar_intent import Clarify, parse_request
from test_lunar_development import AVAILABLE, ENGLISH, HINDI, HINGLISH, call, confirm, draft
import test_lunar_development

ROOT = Path(__file__).resolve().parents[1]


class AnnualIntentTests(unittest.TestCase):
    def test_year_is_explicit_in_three_languages(self):
        for text in (ENGLISH + " every year", HINDI + " हर साल", HINGLISH + " har saal"):
            with self.subTest(text=text):
                rule = parse_request(text)
                self.assertEqual(rule["annual_year"], 2027)
                self.assertEqual(rule["rule"]["month"], "chaitra")
        self.assertNotIn("annual_year", parse_request(ENGLISH))

    def test_annual_request_requires_named_month_and_year(self):
        for text in (ENGLISH.replace("Chaitra ", ""), ENGLISH.replace("2027", "2027-04-15")):
            with self.subTest(text=text), self.assertRaises(Clarify):
                parse_request(text + " annually")

    def test_annual_migration_stays_isolated_and_additive(self):
        from database.migrate import render_migrations

        path = ROOT / "database/migrations/0010_synthetic_annual_lunar_rules.sql"
        source = path.read_text()
        self.assertIn("session_user<>'synthetic_test'", source)
        self.assertIn("current_database()<>'dincharya_app_test'", source)
        self.assertIn("Annual appointment year already used", source)
        self.assertIn("p_expires<=clock_timestamp()", source)
        self.assertTrue(render_migrations([path]).endswith("COMMIT;\n"))


@unittest.skipUnless(AVAILABLE, "optional pinned astronomy dependencies")
class AnnualApprovalTests(unittest.TestCase):
    def setUp(self):
        test_lunar_development.ReviewTests.setUp(self)

    def test_year_draft_is_read_only_then_approval_has_no_projection(self):
        self.owner.approve_annual_rule.return_value = {"status": "approved"}
        preview = draft(self.service, ENGLISH + " annually")
        self.assertEqual(preview["status"], "rule_preview")
        self.assertEqual(self.owner.mock_calls, [])
        self.calendar.assert_not_called()
        result = confirm(self.service, preview["review"])
        self.assertEqual(result["status"], "annual_rule_approved")
        self.assertEqual(confirm(self.service, preview["review"], "new-update"), result)
        self.owner.approve_annual_rule.assert_called_once()
        self.calculator.record_calculation.assert_not_called()
        self.owner.propose_occurrence.assert_not_called()

    def test_ambiguous_month_request_and_expired_or_cancelled_preview_do_not_write(self):
        self.assertEqual(draft(self.service, ENGLISH.replace("ordinary", "both") + " annually")["status"], "clarify")
        preview = draft(self.service, ENGLISH + " annually")
        cancel = {"operation": "cancel_lunar_draft", "review": preview["review"]}
        self.assertEqual(call(self.service, cancel)["status"], "rejected")
        self.assertEqual(confirm(self.service, preview["review"])["status"], "withheld")
        expired = draft(self.service, ENGLISH + " annually")
        self.now += 1800
        self.assertEqual(confirm(self.service, expired["review"])["status"], "withheld")
        self.assertEqual(self.owner.mock_calls, [])

    def test_year_is_revalidated_before_appointment_approval(self):
        from prototypes.panchang.astronomy import Unsupported

        series = str(uuid4())
        rule = dict(parse_request(ENGLISH)["rule"], profile=self.service.development.profile)
        self.owner.inspect_annual_rule.return_value = {
            "series": dict(enabled=True, purpose="monthly", rule=rule, revision=1),
            "annual": dict(title="Family puja", appointment_time="18:00", start_year=2027),
        }
        preview = call(self.service, dict(operation="resume_lunar_annual", series=series, year=2027))
        self.assertEqual(preview["status"], "occurrence_preview")

        def changed(rule, start, end):
            if (end - start).days > 350:
                raise Unsupported("multiple_occurrences_require_narrower_window")
            return test_lunar_development.selection()

        self.calendar.side_effect = changed
        self.assertEqual(confirm(self.service, preview["review"])["status"], "withheld")
        self.owner.decide_annual_review.assert_not_called()
