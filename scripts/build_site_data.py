from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from .catalog import audio_filename, load_test_cases, load_voices
else:
    from catalog import audio_filename, load_test_cases, load_voices


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build docs/data.js from the voice catalog and WAV files."
    )
    parser.add_argument(
        "--voices",
        type=Path,
        default=ROOT / "data" / "voices.csv",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT / "data" / "test-cases.json",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=ROOT / "docs" / "audio",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "data.js",
    )
    return parser.parse_args()


def build_records(
    voices_path: Path,
    cases_path: Path,
    audio_dir: Path,
) -> list[dict[str, object]]:
    cases = load_test_cases(cases_path)
    records: list[dict[str, object]] = []
    for voice in load_voices(voices_path):
        audio = {}
        for test_case in cases:
            filename = audio_filename(voice, test_case.id)
            path = audio_dir / filename
            audio[test_case.id] = (
                f"audio/{filename}"
                if path.is_file() and path.stat().st_size > 0
                else None
            )
        records.append(
            {
                "family": voice.family,
                "familySlug": voice.family_slug,
                "shortName": voice.short_name,
                "localName": voice.local_name,
                "locale": voice.locale,
                "gender": voice.gender,
                "voiceType": voice.voice_type,
                "status": voice.status,
                "styles": list(voice.styles),
                "audio": audio,
            }
        )
    return records


def main() -> int:
    args = parse_args()
    records = build_records(args.voices, args.cases, args.audio_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    args.output.write_text(
        f"window.VOICE_DATA={payload};\n",
        encoding="utf-8",
    )
    available = sum(
        source is not None
        for record in records
        for source in record["audio"].values()
    )
    print(f"Wrote {len(records)} voices and {available} audio links to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
