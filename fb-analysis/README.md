# Snapmaker U1 Facebook Feedback Analysis

Analyzes user feedback from the Snapmaker U1 Official Facebook Group. Classifies posts into a detailed category hierarchy, performs sentiment analysis, and generates a professional PPTX report.

## Features

- **Multi-label classification** using keyword + regex pattern matching (no external API required)
- **Bilingual support**: English and Traditional Chinese (Facebook auto-translation)
- **Sentiment analysis** with satisfaction scoring (1-5 scale)
- **Professional PPTX report** (~15-20 slides) with charts and statistics
- **Competitor mention tracking** (Bambu Lab, Prusa, Creality, etc.)
- **Feature request extraction** and ranking

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run analysis
python analyze.py facebook_data.json

# Specify output directory
python analyze.py facebook_data.json --output ./reports/
```

## Input Data Format

Expects a JSON file exported from the Facebook group with the following structure:

```json
{
  "group_url": "https://www.facebook.com/groups/snapmakeru1/",
  "group_name": "Snapmaker U1 Official Group",
  "total_posts": 188,
  "total_comments": 200,
  "posts": [...],
  "comments_flat": [...]
}
```

## Output

- `output/analysis_result.json` — Intermediate analysis results (per-post classification & sentiment)
- `output/report.pptx` — Professional PPTX presentation report

## Classification Categories

| Code | Category | Subcategories |
|------|----------|---------------|
| H | Hardware | Toolhead, Print Quality, Mechanical, Electrical |
| S | Software | Orca Slicer, Firmware, App, Feature Requests |
| M | Material | Compatibility, Feeding/Clogging, Moisture |
| U | User Experience | Shipping, Setup, Usage, After-sales |
| P | Positive | Quality praise, Multi-color, Value, Community |
| O | Other | Questions, Mods, Competitor comparison |

## Project Structure

```
fb-analysis/
├── analyze.py              # Main entry point
├── classifier.py           # Multi-label classification engine
├── sentiment.py            # Sentiment analysis
├── report_generator.py     # PPTX report generation
├── keywords/               # Keyword dictionaries (JSON)
│   ├── hardware.json
│   ├── software.json
│   ├── material.json
│   ├── ux.json
│   ├── positive.json
│   └── sentiment.json
├── requirements.txt
└── output/                 # Generated reports
```
