from pathlib import Path
from typing import Dict, List, Optional


class StepImporter:
    """Imports raw natural language steps from txt/csv/xlsx files."""

    SUPPORTED = {".txt", ".csv", ".xls", ".xlsx"}

    def import_steps(self, file_path: Path, text_column: Optional[str] = None) -> List[str]:
        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED:
            raise ValueError(f"Unsupported file type: {suffix}")

        if suffix == ".txt":
            return self._from_txt(file_path)
        if suffix == ".csv":
            return self._from_table(file_path, text_column, is_excel=False)
        return self._from_table(file_path, text_column, is_excel=True)

    def import_step_result_pairs(
        self,
        file_path: Path,
        step_column: Optional[str] = None,
        expected_column: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Import row-wise step + expected-result pairs from CSV/Excel tables."""
        suffix = file_path.suffix.lower()
        if suffix not in {".csv", ".xls", ".xlsx"}:
            raise ValueError("Pair import supports csv/xls/xlsx only")

        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "pandas is required for CSV/Excel import. Install with: pip install pandas openpyxl"
            ) from exc

        df = pd.read_excel(file_path) if suffix in {".xls", ".xlsx"} else pd.read_csv(file_path)
        if df.empty:
            return []

        step_col = self._resolve_column(
            df,
            preferred=step_column,
            fallback_candidates=["steps (step)", "step", "test_step", "text", "instruction", "description"],
        )
        expected_col = self._resolve_column(
            df,
            preferred=expected_column,
            fallback_candidates=[
                "steps (expected result)",
                "expected result",
                "expected_result",
                "result",
                "expected",
            ],
        )

        pairs: List[Dict[str, str]] = []
        for _, row in df.iterrows():
            step_text = "" if row.get(step_col) is None else str(row.get(step_col)).strip()
            expected_text = "" if row.get(expected_col) is None else str(row.get(expected_col)).strip()
            if not step_text and not expected_text:
                continue
            pairs.append({"step_text": step_text, "expected_result": expected_text})

        return pairs

    def _from_txt(self, file_path: Path) -> List[str]:
        with file_path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]
        return [line for line in lines if line]

    def _from_table(self, file_path: Path, text_column: Optional[str], is_excel: bool) -> List[str]:
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "pandas is required for CSV/Excel import. Install with: pip install pandas openpyxl"
            ) from exc

        df = pd.read_excel(file_path) if is_excel else pd.read_csv(file_path)
        if df.empty:
            return []

        selected = self._resolve_column(
            df,
            preferred=text_column,
            fallback_candidates=["step", "test_step", "text", "instruction", "description"],
        )
        series = df[selected]

        return [str(v).strip() for v in series.dropna().tolist() if str(v).strip()]

    def _resolve_column(self, df, preferred: Optional[str], fallback_candidates: List[str]):
        if preferred and preferred in df.columns:
            return preferred

        lower_map = {str(c).lower(): c for c in df.columns}
        for candidate in fallback_candidates:
            if candidate in lower_map:
                return lower_map[candidate]

        return df.columns[0]
