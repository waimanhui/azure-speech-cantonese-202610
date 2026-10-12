from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.catalog import audio_filename, load_test_cases, load_voices


ROOT = Path(__file__).resolve().parents[1]


class CatalogTests(unittest.TestCase):
    def test_repository_catalog_and_cases_are_valid(self) -> None:
        voices = load_voices(ROOT / "data" / "voices.csv")
        cases = load_test_cases(ROOT / "data" / "test-cases.json")

        self.assertEqual(170, len(voices))
        self.assertEqual(["01", "02", "03", "04"], [case.id for case in cases])
        self.assertEqual(
            "output_dragon-hd_ar-AE-Rashid_DragonHDLatestNeural_01.wav",
            audio_filename(voices[0], "01"),
        )

    def test_duplicate_voice_is_rejected(self) -> None:
        headers = [
            "voice_family",
            "short_name",
            "local_name",
            "locale",
            "gender",
            "voice_type",
            "status",
            "style_list",
        ]
        row = ["Standard Neural", "zh-HK-TestNeural", "Test", "zh-HK", "Female", "OnlineStandard", "Preview", ""]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "voices.csv"
            with path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.writer(target)
                writer.writerow(headers)
                writer.writerow(row)
                writer.writerow(row)

            with self.assertRaisesRegex(ValueError, "duplicate voice"):
                load_voices(path)


if __name__ == "__main__":
    unittest.main()
