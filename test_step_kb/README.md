# Test Step Knowledge Base

This project builds a Test Step Knowledge Base for phone/VoIP testing.

## Responsibilities by module

- `parser/normalizer.py`: normalizes raw natural-language test steps.
- `parser/pattern_matcher.py`: matches normalized text to pattern library regex rules and extracts parameters.
- `parser/step_parser.py`: full parsing pipeline to produce Action Schema JSON.
- `parser/assertion_parser.py`: expected-result parsing pipeline to produce Assertion Schema JSON.
- `knowledge_base/actions.json`: action enums and parameter schema library.
- `knowledge_base/assertions.json`: assertion enums and parameter schema library.
- `knowledge_base/step_patterns.json`: step pattern library (pattern, regex, mapping, examples).
- `knowledge_base/assertion_patterns.json`: assertion pattern library for expected results.
- `knowledge_base/test_steps.json`: test step dataset with frequency tracking and parsed results.
- `tools/import_steps.py`: batch import from txt/csv/xls/xlsx.
- `tools/build_kb.py`: build/update KB and detect unknown expressions for dynamic pattern growth.
- `main.py`: CLI entrypoint.

## CLI examples

```bash
python main.py parse --text "Press Emergency call"
python main.py import --input ./sample_steps.txt
python main.py import --input ./sample_steps.xlsx --column "Step"
python main.py add-pattern --pattern-file ./new_pattern.json
python main.py rebuild-excel --input ./RQPLEIAD.xlsx --column "Steps (Step)"
python main.py analyze-unknowns --top 30
python main.py parse-expected --text "Display the create key screen"
python main.py ingest-testrail --input ./RQPLEIAD.xlsx --step-column "Steps (Step)" --expected-column "Steps (Expected Result)" --reset
```

## Operational workflow (recommended)

1. Clean rebuild from source file (avoid duplicate append when benchmarking).
2. Analyze unknown expressions and prioritize top frequency items.
3. Add patterns/actions and rebuild again to measure unknown-rate delta.

## Optional embeddings

Install `sentence-transformers` and use:

```bash
python main.py import --input ./sample_steps.csv --embeddings
```

When enabled, each dataset row stores an `embedding` vector for semantic similarity retrieval.
