from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = {
    "voice_family",
    "short_name",
    "local_name",
    "locale",
    "gender",
    "voice_type",
    "status",
    "style_list",
}


@dataclass(frozen=True)
class Voice:
    family: str
    short_name: str
    local_name: str
    locale: str
    gender: str
    voice_type: str
    status: str
    styles: tuple[str, ...]

    @property
    def family_slug(self) -> str:
        return slugify(self.family)


@dataclass(frozen=True)
class TestCase:
    id: str
    name: str
    text: str


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def load_voices(path: Path) -> list[Voice]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or ())
        if missing:
            columns = ", ".join(sorted(missing))
            raise ValueError(f"{path} is missing required columns: {columns}")

        voices: list[Voice] = []
        seen: set[str] = set()
        for line_number, row in enumerate(reader, start=2):
            short_name = row["short_name"].strip()
            if not short_name:
                raise ValueError(f"{path}:{line_number} has an empty short_name")
            if short_name in seen:
                raise ValueError(
                    f"{path}:{line_number} contains duplicate voice {short_name!r}"
                )
            seen.add(short_name)
            voices.append(
                Voice(
                    family=row["voice_family"].strip(),
                    short_name=short_name,
                    local_name=row["local_name"].strip(),
                    locale=row["locale"].strip(),
                    gender=row["gender"].strip(),
                    voice_type=row["voice_type"].strip(),
                    status=row["status"].strip(),
                    styles=tuple(
                        style.strip()
                        for style in row["style_list"].split(",")
                        if style.strip()
                    ),
                )
            )

    if not voices:
        raise ValueError(f"{path} contains no voices")
    return voices


def load_test_cases(path: Path) -> list[TestCase]:
    raw_cases: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError(f"{path} must contain a non-empty JSON array")

    cases: list[TestCase] = []
    seen: set[str] = set()
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise ValueError(f"{path} contains a non-object test case")
        try:
            case = TestCase(
                id=str(raw_case["id"]).strip(),
                name=str(raw_case["name"]).strip(),
                text=str(raw_case["text"]).strip(),
            )
        except KeyError as error:
            raise ValueError(f"{path} test case is missing {error.args[0]!r}") from error
        if not case.id or not case.name or not case.text:
            raise ValueError(f"{path} contains an empty test-case field")
        if case.id in seen:
            raise ValueError(f"{path} contains duplicate test-case ID {case.id!r}")
        seen.add(case.id)
        cases.append(case)
    return cases


def audio_filename(voice: Voice, case_id: str) -> str:
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", voice.short_name)
    return f"output_{voice.family_slug}_{safe_name}_{case_id}.wav"
