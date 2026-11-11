"""Offline checks for publication and assignment denominators."""

import unittest

from revision_analysis import summarize, parse_tags, validate_records


class CountingTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {"id": "r1", "year": 2016, "tags": {"Domain": {"D", "E"}, "Models": {"A", "B"}}},
            {"id": "r2", "year": 2016, "tags": {"Domain": {"D"}, "Models": {"A"}}},
            {"id": "r3", "year": 2017, "tags": {"Domain": {"E"}, "Models": set()}},
        ]

    def test_binary_tags_are_deduplicated(self):
        self.assertEqual(parse_tags("A; A ; B"), {"A", "B"})
        self.assertEqual(parse_tags(None), set())

    def test_publication_prevalence_and_assignment_share_differ(self):
        result = summarize(self.records, ["Domain", "Models"])
        a = next(x for x in result["annual"] if x["year"] == 2016 and x["dimension"] == "Models" and x["category"] == "A")
        b = next(x for x in result["annual"] if x["year"] == 2016 and x["dimension"] == "Models" and x["category"] == "B")
        self.assertEqual(a["count"], 2)
        self.assertEqual(a["prevalence_pct"], 100)
        self.assertEqual(b["prevalence_pct"], 50)
        self.assertAlmostEqual(a["assignment_share_pct"], 200 / 3)
        self.assertAlmostEqual(b["assignment_share_pct"], 100 / 3)

    def test_coverage_uses_unique_records_and_zero_assignments_are_na(self):
        result = summarize(self.records, ["Domain", "Models"])
        coverage = next(x for x in result["coverage"] if x["year"] == 2016 and x["dimension"] == "Models")
        self.assertEqual(coverage["tagged"], 2)
        self.assertEqual(coverage["coverage_pct"], 100)
        empty = next(x for x in result["annual"] if x["year"] == 2017 and x["dimension"] == "Models")
        self.assertEqual(empty["prevalence_pct"], 0)
        self.assertIsNone(empty["assignment_share_pct"])

    def test_cross_sections_count_once_per_record(self):
        result = summarize(self.records, ["Domain", "Models"], domain_dimension="Domain")
        cell = next(x for x in result["cross"] if x["domain"] == "D" and x["category"] == "A")
        self.assertEqual(cell["count"], 2)
        self.assertEqual(cell["domain_records"], 2)
        self.assertEqual(cell["category_records"], 2)
        self.assertEqual(cell["within_domain_prevalence_pct"], 100)
        self.assertTrue(all(x["count"] <= min(x["domain_records"], x["category_records"]) for x in result["cross"]))

    def test_repeated_identifiers_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_records(self.records + [self.records[0]])

    def test_out_of_window_year_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_records([{"id": "bad", "year": 2015, "tags": {}}])

    def test_empty_cohort_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_records([])


if __name__ == "__main__":
    unittest.main()
