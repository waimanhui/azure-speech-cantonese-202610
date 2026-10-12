from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_site_data import build_records


ROOT = Path(__file__).resolve().parents[1]


class SiteDataTests(unittest.TestCase):
    def test_only_non_empty_audio_is_published(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            audio_dir = Path(directory)
            filename = (
                "output_dragon-hd_"
                "ar-AE-Rashid_DragonHDLatestNeural_01.wav"
            )
            (audio_dir / filename).write_bytes(b"RIFF")
            (audio_dir / filename.replace("_01.wav", "_02.wav")).touch()

            records = build_records(
                ROOT / "data" / "voices.csv",
                ROOT / "data" / "test-cases.json",
                audio_dir,
            )

        self.assertEqual(f"audio/{filename}", records[0]["audio"]["01"])
        self.assertIsNone(records[0]["audio"]["02"])


if __name__ == "__main__":
    unittest.main()
