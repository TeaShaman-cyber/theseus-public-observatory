import unittest
from datetime import datetime, timezone

from scripts.schumann_read import parse_matrix, read_nck

UTC = timezone.utc
START = datetime(2023, 2, 10, tzinfo=UTC)
END = datetime(2023, 2, 11, tzinfo=UTC)


def fixture():
    dates = [f"2023/02/{d:02}" for d in range(10, 21)]
    lines = ["Time [UT]\t" + "\t".join(dates) + "\t"]
    for i in range(48):
        lines.append(
            str(i / 2) + "\t" + "\t".join(["NaN" if i == 0 else "7.9"] * 11) + "\t"
        )
    return "\n".join(lines).encode()


class SchumannTests(unittest.TestCase):
    def test_matrix_uses_date_and_half_hour_tag_without_inventing_support(self):
        result = parse_matrix(fixture())
        self.assertEqual(len(result), 528)
        self.assertIsNone(result["2023-02-10T00:00:00Z"])
        self.assertEqual(result["2023-02-20T23:30:00Z"], 7.9)

    def test_rejects_malformed_grid_and_values(self):
        raw = fixture()
        for bad in (
            raw.replace(b"2023/02/11", b"2023/02/10"),
            raw.replace(b"0.5\t", b"0.0\t"),
            raw.replace(b"7.9", b"inf"),
            raw.replace(b"7.9", b"0"),
            raw[:-10],
        ):
            with self.subTest(bad=bad[:50]), self.assertRaises(ValueError):
                parse_matrix(bad)

    def test_no_outside_coverage_or_model_selection(self):
        with self.assertRaises(ValueError):
            read_nck(datetime(2023, 2, 9, tzinfo=UTC), END)
        with self.assertRaises(ValueError):
            read_nck(START, END, modes=[4])
