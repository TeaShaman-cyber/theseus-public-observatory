import unittest
from report import read_lcov, score


class ReportTests(unittest.TestCase):
    def test_branch_preferred_and_unknown_distinct(self):
        cov = read_lcov(
            "SF:scripts/a.py\nDA:1,1\nDA:2,1\nDA:3,0\nBRDA:2,0,0,1\nBRDA:2,0,1,-\nend_of_record\n"
        )
        self.assertEqual(score(4, 1, 3, cov["scripts/a.py"]), (1, 2, "branch", 6.0))
        self.assertEqual(score(4, 4, 8, cov["scripts/a.py"]), (0, 0, "unknown", None))
        self.assertEqual(score(4, 1, 3, None), (0, 0, "unknown", None))

    def test_line_fallback_zero_is_measured(self):
        cov = read_lcov("SF:scripts/a.py\nDA:4,0\nDA:5,0\nend_of_record\n")
        self.assertEqual(score(5, 4, 5, cov["scripts/a.py"]), (0, 2, "line", 30.0))

    def test_duplicate_record_fails_closed(self):
        with self.assertRaises(ValueError):
            read_lcov("SF:a.py\nDA:1,1\nDA:1,0\nend_of_record\n")

    def test_calibrate_complexity_and_nested_unit(self):
        from crapper.languages import functions_in_file

        python = "def outer(a):\n    def inner(b):\n        if b:\n            return 1\n        return 0\n    if a:\n        return inner(a)\n    return 0\n"
        units = functions_in_file("python", python, "scripts/a.py", ".")
        self.assertEqual(
            [(f.name, f.complexity, f.start_line, f.end_line) for f in units],
            [("outer", 3, 1, 8)],
        )
        js = "function f(a) {\n if (a) return 1;\n return 0;\n}\n"
        units = functions_in_file("typescript", js, "scripts/a.mjs", ".")
        self.assertEqual(
            [(f.name, f.complexity, f.start_line, f.end_line) for f in units],
            [("f", 2, 1, 4)],
        )
