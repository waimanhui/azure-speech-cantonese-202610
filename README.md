# Azure Speech Cantonese Voice Gallery

A reproducible Azure AI Speech listening test for Cantonese. The repository
contains:

- a CSV catalog of 170 Azure voices;
- a Python generator for four fixed Cantonese test cases;
- pre-generated WAV samples; and
- a static listening gallery ready for GitHub Pages.

Check the GitHub page to listen to the audio samples for the Azure Speech voices.</BR>
https://waimanhui.github.io/azure-speech-cantonese-202610/

## Voice family observations

Voice availability and subjective observations were checked on **11 October
2026** using the four Cantonese test cases. Results may vary
with different text, speaking styles, synthesis settings, and subsequent Azure
Speech updates.

| Voice family | Listening observations | Recommendation |
|---|---|---|
| **Dragon HD** | - Generally the most natural-sounding family.<br>- Relatively authentic Cantonese accents.<br>- Most voices handle Cantonese-English code-switching well.<br>- English phrases retain suitable intonation without disrupting the Cantonese flow. | **Most recommended.** Start evaluation with this family. |
| **Dragon HD Omni** | - Smooth, controlled delivery similar to Dragon HD Latest.<br>- Many voices retain a noticeable non-native accent when speaking Cantonese. | Consider when smooth delivery matters more than local accent authenticity. |
| **Multilingual Neural** | - The listed voices support the `zh-HK` locale.<br>- Most have a less pronounced non-native accent than broader multilingual options.<br>- English phrases often retain natural English intonation.<br>- The contrast can make Cantonese-English transitions sound flatter or less integrated. | Useful for multilingual content where clear English pronunciation is important. |
| **Standard Neural** | - The listed voices support `zh-HK` and are relatively fluent in Cantonese.<br>- Voices from `zh-HK`, `zh-CN`, and `yue-CN` generally sound more locally natural.<br>- Voices from other locales often retain a non-native accent.<br>- English phrases may preserve their original intonation, making code-switching sound less integrated.<br>- Within this family, `DragonLatestNeural` voices generally handle Cantonese-English tone transitions better than the other Standard Neural voices. | **Second recommendation.** Evaluate `DragonLatestNeural` voices after Dragon HD Latest. |

## Generate the audio yourself

### Prerequisites

- Python 3.10 or newer
- A Microsoft Foundry resource with Azure AI Speech enabled
- Permission to access the resource with Microsoft Entra ID

### Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your Foundry resource endpoint and full Azure resource ID:

```dotenv
FOUNDRY_ENDPOINT=https://<resource-name>.cognitiveservices.azure.com/
FOUNDRY_RESOURCE_ID=/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<resource-name>
```

Authenticate before running the generator:

```powershell
az login
```


### Run

Validate the catalog and see what would be generated without calling Azure:

```powershell
python scripts\generate_audio.py --dry-run --limit 1
```

Generate all four cases for one voice:

```powershell
python scripts\generate_audio.py --voice "zh-HK-HiuMaanNeural"
```

Generate one case for the first five voices:

```powershell
python scripts\generate_audio.py --case 01 --limit 5
```

Generate every missing sample:

```powershell
python scripts\generate_audio.py
```

Existing non-empty WAV files are skipped. Pass `--overwrite` to replace them,
or `--after "<short_name>"` to resume after a specific voice.

After generating files, rebuild the browser data:

```powershell
python scripts\build_site_data.py
```

Commit changes under `docs/audio/` and `docs/data.js` when you want the new
samples included in the public gallery.

## Project structure

```text
.
|-- .github/
|   `-- workflows/
|       `-- pages.yml            # Publishes docs/ to GitHub Pages
|-- data/
|   |-- test-cases.json          # Canonical test prompts
|   `-- voices.csv               # Canonical voice catalog
|-- docs/
|   |-- audio/                   # Generated and pre-generated WAV files
|   |-- app.js                   # Gallery filtering and audio player
|   |-- data.js                  # Generated voice/audio availability index
|   |-- index.html               # Static listening gallery
|   `-- styles.css               # Gallery presentation
|-- scripts/
|   |-- build_site_data.py       # Rebuilds docs/data.js
|   |-- catalog.py               # Shared CSV/filename validation
|   `-- generate_audio.py        # Foundry-backed Speech batch generator
|-- tests/
|   |-- test_catalog.py          # Catalog and filename validation
|   `-- test_site_data.py        # Published-audio index validation
|-- .editorconfig                # Cross-editor formatting defaults
|-- .env.example                # Safe Foundry configuration template
|-- .gitattributes              # Text and WAV Git handling
|-- .gitignore                  # Credentials, caches, and local outputs
|-- README.md                   # Setup and usage guide
`-- requirements.txt            # Python runtime dependencies
```

Create a local `.env` from `.env.example`. It is intentionally excluded from
the tree above because `.env` contains environment-specific resource details
and is ignored by Git.

## CSV format

`data/voices.csv` must include these headers:

```text
voice_family,short_name,local_name,locale,gender,voice_type,status,style_list
```

`short_name` values must be unique. `style_list` may contain comma-separated
styles. The generator fails with a clear error for missing columns, duplicate
voices, unknown voice/case selections, or invalid limits.

## Validation

The test suite is offline and does not require Azure credentials:

```powershell
python -m unittest discover -s tests -v
python scripts\generate_audio.py --dry-run --limit 1
python scripts\build_site_data.py
```
