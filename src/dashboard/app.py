"""Streamlit dashboard for Purdue syllabi analysis results."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parents[2] / "data"
RESULTS_DIR = DATA_DIR / "results"
PROGRAMS_FILE = DATA_DIR / "programs.json"

RUBRIC_SECTIONS = {
    "pillars": "Pillars",
    "rigor": "Rigor",
    "student_agency_and_responsibility": "Student Agency & Responsibility",
    "demonstrable_evidence_of_learning": "Demonstrable Evidence of Learning",
    "exclusions": "Exclusions",
}


def load_department(dept_file: Path) -> list[dict]:
    """Load a single department JSON results file."""
    with open(dept_file, encoding="utf-8") as f:
        return [r for r in json.load(f) if "_error" not in r]


def get_departments() -> dict[str, Path]:
    """Return a mapping of department name -> json file path."""
    return {
        p.stem: p
        for p in sorted(RESULTS_DIR.glob("*.json"))
    }


def load_all_courses() -> list[dict]:
    """Load all courses from every department results file."""
    all_courses = []
    for dept_file in RESULTS_DIR.glob("*.json"):
        all_courses.extend(load_department(dept_file))
    return all_courses


def get_programs() -> dict[str, list[str]]:
    """Return a mapping of program name -> list of course numbers."""
    if not PROGRAMS_FILE.exists():
        return {}
    with open(PROGRAMS_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_program_courses(program_courses: list[str], all_courses: list[dict]) -> list[dict]:
    """Filter all courses to those matching a program's course list."""
    # Normalize course numbers for matching (strip spaces, uppercase)
    normalized = {c.replace(" ", "").upper() for c in program_courses}
    return [
        c for c in all_courses
        if (c["course_information"].get("course_number") or "").replace(" ", "").upper() in normalized
    ]


def render_decision_badge(decision: str):
    """Render a colored badge for the review decision."""
    colors = {
        "approved": "green",
        "not_approved": "red",
        "deferred": "orange",
    }
    labels = {
        "approved": "Approved",
        "not_approved": "Not Approved",
        "deferred": "Deferred",
    }
    color = colors.get(decision, "gray")
    label = labels.get(decision, decision)
    st.markdown(f":{color}[**{label}**]")


def render_section_summary(section_key: str, section_data: dict):
    """Render a rubric section as a table of criteria with scores and expandable rationales."""
    section_label = RUBRIC_SECTIONS[section_key]
    scores = {k: v["score"] for k, v in section_data.items()}
    total = sum(scores.values())
    count = len(scores)

    if section_key == "exclusions":
        header = f"{section_label} ({total} flagged)"
    else:
        header = f"{section_label} ({total}/{count})"

    with st.expander(header, expanded=False):
        for criterion_key, criterion_data in section_data.items():
            score = criterion_data["score"]
            rationale = criterion_data["rationale"]
            label = criterion_key.replace("_", " ").title()

            if section_key == "exclusions":
                icon = "🚩" if score == 1 else "✅"
            else:
                icon = "✅" if score == 1 else "❌"

            st.markdown(f"{icon} **{label}**")
            st.caption(rationale)


def main():
    st.set_page_config(page_title="Purdue Syllabi Analyzer", layout="wide")
    st.title("Purdue Syllabi Analyzer")

    departments = get_departments()

    if not departments:
        st.warning("No analysis results found. Run the analysis first: `python -m src.analysis.analyze`")
        return

    programs = get_programs()

    # Sidebar: navigation
    st.sidebar.header("Navigation")

    view_options = ["Department"]
    if programs:
        view_options.append("Program")
    view_mode = st.sidebar.radio("View by", view_options)

    if view_mode == "Program":
        selected_program = st.sidebar.selectbox("Program", list(programs.keys()))
        all_courses = load_all_courses()
        results = load_program_courses(programs[selected_program], all_courses)

        if not results:
            st.info(f"No matching results for **{selected_program}**. Check that the course numbers in `data/programs.json` match analyzed courses.")
            return

        summary_title = f"{selected_program}"
        missing = [
            c for c in programs[selected_program]
            if c.replace(" ", "").upper() not in {
                (r["course_information"].get("course_number") or "").replace(" ", "").upper()
                for r in results
            }
        ]
    else:
        selected_dept = st.sidebar.selectbox("Department", list(departments.keys()))
        results = load_department(departments[selected_dept])

        if not results:
            st.info(f"No valid results for {selected_dept}.")
            return

        summary_title = f"{selected_dept} Department"
        missing = None

    # Summary
    st.header(f"{summary_title} Summary")

    decisions = [r["course_analysis"]["review_decision"]["decision"] for r in results]
    approved = decisions.count("approved")
    not_approved = decisions.count("not_approved")
    deferred = decisions.count("deferred")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Courses", len(results))
    col2.metric("Approved", approved)
    col3.metric("Not Approved", not_approved)
    col4.metric("Deferred", deferred)

    if missing:
        st.warning(f"Courses not yet analyzed: {', '.join(missing)}")

    # Build course list used by both the table and the sidebar selector
    course_labels = [
        r["course_information"].get("course_number") or r.get("_source_file", "Unknown")
        for r in results
    ]

    # Summary table (clickable)
    summary_df = pd.DataFrame([
        {
            "Course": course_labels[i],
            "Title": r["course_information"].get("course_title") or "",
            "Decision": r["course_analysis"]["review_decision"]["decision"].replace("_", " ").title(),
        }
        for i, r in enumerate(results)
    ])

    event = st.dataframe(
        summary_df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # If a table row was clicked, update the sidebar selectbox value before it renders
    selected_rows = event.selection.rows if event.selection.rows else []
    if selected_rows:
        st.session_state["course_select"] = course_labels[selected_rows[0]]

    # Initialize if not set
    if "course_select" not in st.session_state:
        st.session_state["course_select"] = course_labels[0]

    # Sidebar: course selector (synced with table via session state)
    selected_course = st.sidebar.selectbox(
        "Course", course_labels, key="course_select"
    )

    course_data = results[course_labels.index(selected_course)]

    # Course detail view
    st.divider()
    info = course_data["course_information"]
    analysis = course_data["course_analysis"]

    st.header(f"{info.get('course_number', 'Unknown')} — {info.get('course_title', '')}")

    # Course info
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"**Department:** {info.get('department', 'N/A')}")
    col2.markdown(f"**College:** {info.get('college', 'N/A')}")
    col3.markdown(f"**Review Date:** {info.get('review_date') or 'N/A'}")

    # Decision
    st.subheader("Review Decision")
    render_decision_badge(analysis["review_decision"]["decision"])
    st.caption(analysis["review_decision"]["rationale"])

    # Rubric sections
    st.subheader("Rubric Criteria")
    for section_key in RUBRIC_SECTIONS:
        render_section_summary(section_key, analysis[section_key])


if __name__ == "__main__":
    main()
