import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from tools.build_kb import KnowledgeBaseBuilder
from tools.import_steps import StepImporter


def _load_pattern_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _reset_dataset(kb_dir: Path) -> None:
    payload = {
        "meta": {"version": "1.0", "total_steps": 0, "unknown_steps": 0},
        "frequency": {"actions": {}, "patterns": {}},
        "steps": [],
    }
    dataset = kb_dir / "test_steps.json"
    with dataset.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _print_unknown_report(kb_dir: Path, top_n: int) -> None:
    dataset = kb_dir / "test_steps.json"
    with dataset.open("r", encoding="utf-8") as f:
        data = json.load(f)

    unknown_counter = Counter()
    for row in data.get("steps", []):
        parsed = row.get("parsed_action", {})
        if parsed.get("action") == "UNKNOWN":
            normalized = row.get("normalized_text") or ""
            if normalized:
                unknown_counter[normalized] += 1

    report = [
        {"expression": text, "count": count}
        for text, count in unknown_counter.most_common(top_n)
    ]

    unknown_assertion_counter = Counter()
    for row in data.get("steps", []):
        parsed = row.get("parsed_assertion", {})
        if parsed.get("assertion") == "UNKNOWN_ASSERTION":
            normalized = row.get("normalized_expected_result") or ""
            if normalized:
                unknown_assertion_counter[normalized] += 1

    assertion_report = [
        {"expression": text, "count": count}
        for text, count in unknown_assertion_counter.most_common(top_n)
    ]

    print(
        json.dumps(
            {
                "unknown_step_total": sum(unknown_counter.values()),
                "unknown_assertion_total": sum(unknown_assertion_counter.values()),
                "unknown_steps_top": report,
                "unknown_assertions_top": assertion_report,
            },
            indent=2,
        )
    )


def cli() -> None:
    parser = argparse.ArgumentParser(description="Test Step Knowledge Base CLI")
    parser.add_argument(
        "--kb-dir",
        default=str(Path(__file__).parent / "knowledge_base"),
        help="Path to knowledge base directory",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="Import and build KB from a raw step file")
    p_import.add_argument("--input", required=True, help="Input file: txt/csv/xls/xlsx")
    p_import.add_argument("--column", default=None, help="Optional step text column name")
    p_import.add_argument("--embeddings", action="store_true", help="Enable embeddings if installed")

    p_add = sub.add_parser("add-pattern", help="Add one pattern JSON into step pattern library")
    p_add.add_argument("--pattern-file", required=True, help="Path to single pattern JSON file")

    p_parse = sub.add_parser("parse", help="Parse one step text and print Action Schema JSON")
    p_parse.add_argument("--text", required=True, help="Raw test step text")

    p_parse_expected = sub.add_parser(
        "parse-expected",
        help="Parse one expected-result text and print Assertion Schema JSON",
    )
    p_parse_expected.add_argument("--text", required=True, help="Raw expected result text")

    p_rebuild = sub.add_parser(
        "rebuild-excel",
        help="Reset dataset and rebuild KB from one Excel/CSV/TXT source",
    )
    p_rebuild.add_argument("--input", required=True, help="Input file: txt/csv/xls/xlsx")
    p_rebuild.add_argument("--column", default=None, help="Step text column name")
    p_rebuild.add_argument("--embeddings", action="store_true", help="Enable embeddings if installed")

    p_unknown = sub.add_parser("analyze-unknowns", help="Print top unknown expressions from dataset")
    p_unknown.add_argument("--top", type=int, default=20, help="Top-N unknown expressions")

    p_ingest = sub.add_parser(
        "ingest-testrail",
        help="Ingest TestRail-style table with step and expected-result columns",
    )
    p_ingest.add_argument("--input", required=True, help="Input file: csv/xls/xlsx")
    p_ingest.add_argument("--step-column", default="Steps (Step)", help="Step column name")
    p_ingest.add_argument(
        "--expected-column",
        default="Steps (Expected Result)",
        help="Expected result column name",
    )
    p_ingest.add_argument("--reset", action="store_true", help="Reset dataset before ingest")
    p_ingest.add_argument("--embeddings", action="store_true", help="Enable embeddings if installed")

    args = parser.parse_args()
    kb_dir = Path(args.kb_dir)

    if args.command == "import":
        importer = StepImporter()
        steps = importer.import_steps(Path(args.input), args.column)
        builder = KnowledgeBaseBuilder(kb_dir=kb_dir, enable_embeddings=args.embeddings)
        stats = builder.build(steps)
        print(json.dumps({"status": "ok", "imported": len(steps), "stats": stats}, indent=2))
        return

    if args.command == "add-pattern":
        builder = KnowledgeBaseBuilder(kb_dir=kb_dir)
        pattern = _load_pattern_json(Path(args.pattern_file))
        builder.add_pattern(pattern)
        print(json.dumps({"status": "ok", "added_pattern_id": pattern.get("pattern_id")}, indent=2))
        return

    if args.command == "parse":
        builder = KnowledgeBaseBuilder(kb_dir=kb_dir)
        parsed = builder.parser.parse(step_number=1, raw_text=args.text)
        print(json.dumps(builder.parser.to_action_schema_json(parsed), indent=2))
        return

    if args.command == "parse-expected":
        builder = KnowledgeBaseBuilder(kb_dir=kb_dir)
        parsed = builder.assertion_parser.parse(args.text)
        print(json.dumps(builder.assertion_parser.to_assertion_schema_json(parsed), indent=2))
        return

    if args.command == "rebuild-excel":
        _reset_dataset(kb_dir)
        importer = StepImporter()
        steps = importer.import_steps(Path(args.input), args.column)
        builder = KnowledgeBaseBuilder(kb_dir=kb_dir, enable_embeddings=args.embeddings)
        stats = builder.build(steps)
        print(json.dumps({"status": "ok", "rebuilt": len(steps), "stats": stats}, indent=2))
        return

    if args.command == "analyze-unknowns":
        _print_unknown_report(kb_dir, args.top)
        return

    if args.command == "ingest-testrail":
        if args.reset:
            _reset_dataset(kb_dir)

        importer = StepImporter()
        pairs = importer.import_step_result_pairs(
            Path(args.input),
            step_column=args.step_column,
            expected_column=args.expected_column,
        )
        builder = KnowledgeBaseBuilder(kb_dir=kb_dir, enable_embeddings=args.embeddings)
        stats = builder.build_pairs(pairs)
        print(json.dumps({"status": "ok", "ingested": len(pairs), "stats": stats}, indent=2))
        return


if __name__ == "__main__":
    cli()
