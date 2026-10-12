from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

if __package__:
    from .catalog import (
        TestCase,
        Voice,
        audio_filename,
        load_test_cases,
        load_voices,
    )
else:
    from catalog import (
        TestCase,
        Voice,
        audio_filename,
        load_test_cases,
        load_voices,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VOICES = ROOT / "data" / "voices.csv"
DEFAULT_CASES = ROOT / "data" / "test-cases.json"
DEFAULT_OUTPUT = ROOT / "docs" / "audio"


class SpeechClient:
    def __init__(self) -> None:
        endpoint = require_environment("FOUNDRY_ENDPOINT")
        key = os.getenv("SPEECH_KEY")
        self._credential: DefaultAzureCredential | None = None
        self._resource_id: str | None = None
        self._token_expires_on = 0

        if key:
            self.config = speechsdk.SpeechConfig(
                subscription=key,
                endpoint=endpoint,
            )
        else:
            self._resource_id = require_environment("FOUNDRY_RESOURCE_ID")
            self._credential = DefaultAzureCredential(
                exclude_interactive_browser_credential=False
            )
            self.config = speechsdk.SpeechConfig(endpoint=endpoint)
            self.refresh_token(force=True)

        self.config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
        )

    def refresh_token(self, force: bool = False) -> None:
        if self._credential is None or self._resource_id is None:
            return
        if not force and self._token_expires_on - time.time() >= 600:
            return
        token = self._credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        )
        self.config.authorization_token = (
            f"aad#{self._resource_id}#{token.token}"
        )
        self._token_expires_on = token.expires_on

    def synthesize(self, ssml: str, output_path: Path) -> tuple[bool, str]:
        self.refresh_token()
        for attempt in range(2):
            audio_config = speechsdk.audio.AudioOutputConfig(
                filename=str(output_path)
            )
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.config,
                audio_config=audio_config,
            )
            result = synthesizer.speak_ssml_async(ssml).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                if output_path.exists() and output_path.stat().st_size > 0:
                    return True, ""
                return False, "Azure reported success but returned no audio bytes"

            details = result.cancellation_details
            error = details.error_details if details is not None else ""
            authentication_failed = (
                "401" in error or "Authentication error" in error
            )
            if authentication_failed and attempt == 0 and self._credential:
                self.refresh_token(force=True)
                continue
            reason = details.reason if details is not None else result.reason
            return False, f"{reason}: {error}".rstrip(": ")
        return False, "Speech synthesis failed after authentication retry"


def require_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is required. Copy .env.example to .env and configure it."
        )
    return value


def build_ssml(voice: Voice, test_case: TestCase) -> str:
    return (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        'xml:lang="zh-HK">'
        f"<voice name={quoteattr(voice.short_name)}>"
        f'<lang xml:lang="zh-HK">{escape(test_case.text)}</lang>'
        "</voice></speak>"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Azure AI Speech samples from the voice catalog."
    )
    parser.add_argument("--voices", type=Path, default=DEFAULT_VOICES)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--voice", help="Generate one exact short_name.")
    parser.add_argument(
        "--after",
        help="Resume with the voice after this exact short_name.",
    )
    parser.add_argument("--case", dest="case_id", help="Generate one case ID.")
    parser.add_argument("--limit", type=int, help="Limit the selected voices.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing non-empty WAV files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print planned files without calling Azure.",
    )
    args = parser.parse_args()
    if args.voice and args.after:
        parser.error("--voice and --after cannot be used together")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero")
    return args


def select_items(
    voices: list[Voice],
    cases: list[TestCase],
    args: argparse.Namespace,
) -> tuple[list[Voice], list[TestCase]]:
    voice_names = [voice.short_name for voice in voices]
    if args.voice:
        if args.voice not in voice_names:
            raise ValueError(f"Voice not found: {args.voice}")
        voices = [voices[voice_names.index(args.voice)]]
    elif args.after:
        if args.after not in voice_names:
            raise ValueError(f"Resume voice not found: {args.after}")
        voices = voices[voice_names.index(args.after) + 1 :]
    if args.limit is not None:
        voices = voices[: args.limit]

    if args.case_id:
        cases = [case for case in cases if case.id == args.case_id]
        if not cases:
            raise ValueError(f"Test case not found: {args.case_id}")
    return voices, cases


def main() -> int:
    args = parse_args()
    voices, cases = select_items(
        load_voices(args.voices),
        load_test_cases(args.cases),
        args,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(voice, case) for voice in voices for case in cases]
    pending = [
        (voice, case, args.output_dir / audio_filename(voice, case.id))
        for voice, case in jobs
        if args.overwrite
        or not (args.output_dir / audio_filename(voice, case.id)).exists()
        or (args.output_dir / audio_filename(voice, case.id)).stat().st_size == 0
    ]

    print(
        f"Selected {len(voices)} voices and {len(cases)} cases; "
        f"{len(pending)} of {len(jobs)} files need generation."
    )
    if args.dry_run:
        for _, _, output_path in pending:
            print(output_path)
        return 0
    if not pending:
        return 0

    load_dotenv(ROOT / ".env")
    client = SpeechClient()
    failures = 0
    for index, (voice, test_case, output_path) in enumerate(pending, start=1):
        print(
            f"[{index}/{len(pending)}] {voice.short_name} / "
            f"{test_case.id} -> {output_path.name}"
        )
        success, error = client.synthesize(
            build_ssml(voice, test_case),
            output_path,
        )
        if success:
            continue
        failures += 1
        if output_path.exists() and output_path.stat().st_size == 0:
            output_path.unlink()
        print(f"  ERROR: {error}", file=sys.stderr)

    if failures:
        print(f"Generation completed with {failures} failure(s).", file=sys.stderr)
        return 1
    print("Generation completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
