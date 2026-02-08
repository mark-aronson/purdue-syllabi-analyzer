"""Analyze syllabi using the Claude API."""

import anthropic
import base64
import json
import sys
from pathlib import Path

import docx

PROMPT_PATH = Path(__file__).parent / "prompt.txt"
SYLLABI_DIR = Path(__file__).parents[2] / "syllabi"
RESULTS_DIR = Path(__file__).parents[2] / "data" / "results"


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def _extract_docx_text(docx_path: Path) -> str:
    """Extract plain text from a DOCX file."""
    doc = docx.Document(str(docx_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))
    return "\n".join(paragraphs)


def _build_message_content(file_path: Path) -> list[dict]:
    """Build the Claude API message content blocks for a syllabus file."""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        pdf_b64 = base64.standard_b64encode(file_path.read_bytes()).decode("utf-8")
        return [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
            },
            {
                "type": "text",
                "text": "Analyze this syllabus and extract the requested information as JSON.",
            },
        ]
    elif suffix == ".docx":
        text = _extract_docx_text(file_path)
        return [
            {
                "type": "text",
                "text": (
                    f"Below is the text content of a syllabus document ({file_path.name}):\n\n"
                    f"{text}\n\n"
                    "Analyze this syllabus and extract the requested information as JSON."
                ),
            },
        ]
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def analyze_syllabus(client: anthropic.Anthropic, file_path: Path) -> dict:
    """Send a single syllabus (PDF or DOCX) to Claude for analysis and return parsed JSON."""
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        system=load_system_prompt(),
        messages=[
            {
                "role": "user",
                "content": _build_message_content(file_path),
            }
        ],
    )

    return json.loads(message.content[0].text)


def analyze_department(client: anthropic.Anthropic, department: str) -> list[dict]:
    """Analyze all syllabi (PDF and DOCX) in a department subdirectory."""
    dept_dir = SYLLABI_DIR / department
    if not dept_dir.is_dir():
        print(f"Department directory not found: {dept_dir}")
        return []

    files = sorted(
        f for f in dept_dir.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not files:
        print(f"No supported files found in {dept_dir}")
        return []

    results = []
    for file_path in files:
        print(f"  Analyzing {file_path.name}...")
        try:
            result = analyze_syllabus(client, file_path)
            result["_source_file"] = str(file_path.relative_to(SYLLABI_DIR))
            results.append(result)
        except Exception as e:
            print(f"  ERROR processing {file_path.name}: {e}")
            results.append({"_source_file": str(file_path.relative_to(SYLLABI_DIR)), "_error": str(e)})

    return results


def analyze_all(departments: list[str] | None = None):
    """Analyze syllabi for all (or specified) departments and save results."""
    client = anthropic.Anthropic()

    if departments is None:
        departments = sorted(
            d.name for d in SYLLABI_DIR.iterdir() if d.is_dir() and d.name != ".gitkeep"
        )

    if not departments:
        print("No department directories found in syllabi/")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for dept in departments:
        print(f"Processing department: {dept}")
        results = analyze_department(client, dept)

        if results:
            output_path = RESULTS_DIR / f"{dept}.json"
            output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            print(f"  Saved {len(results)} results to {output_path}")


if __name__ == "__main__":
    depts = sys.argv[1:] if len(sys.argv) > 1 else None
    analyze_all(depts)
