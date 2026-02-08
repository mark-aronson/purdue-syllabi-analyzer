"""Streamlit dashboard for Purdue syllabi analysis results."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

RESULTS_DIR = Path(__file__).parents[2] / "data" / "results"


@st.cache_data
def load_results() -> pd.DataFrame:
    """Load all department JSON result files into a single DataFrame."""
    records = []
    for json_path in sorted(RESULTS_DIR.glob("*.json")):
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
            for record in data:
                if "_error" not in record:
                    records.append(record)
    return pd.DataFrame(records)


def main():
    st.set_page_config(page_title="Purdue Syllabi Analyzer", layout="wide")
    st.title("Purdue Syllabi Analyzer")

    df = load_results()

    if df.empty:
        st.warning("No analysis results found. Run the analysis first: `python -m src.analysis.analyze`")
        return

    # Sidebar filters
    st.sidebar.header("Filters")
    departments = sorted(df["department"].dropna().unique())
    selected_depts = st.sidebar.multiselect("Department", departments, default=departments)
    df_filtered = df[df["department"].isin(selected_depts)]

    # Overview metrics
    st.header("Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Syllabi", len(df_filtered))
    col2.metric("Departments", df_filtered["department"].nunique())
    col3.metric("Avg Credits", round(df_filtered["credits"].dropna().mean(), 1) if not df_filtered["credits"].dropna().empty else "N/A")
    col4.metric("Unique Instructors", df_filtered["instructor"].nunique())

    # Department breakdown
    st.header("Courses by Department")
    dept_counts = df_filtered["department"].value_counts().sort_index()
    st.bar_chart(dept_counts)

    # Grading patterns
    st.header("Common Assessment Types")
    if "assignment_types" in df_filtered.columns:
        all_types = []
        for types in df_filtered["assignment_types"].dropna():
            if isinstance(types, list):
                all_types.extend(t.lower().strip() for t in types)
        if all_types:
            type_counts = pd.Series(all_types).value_counts().head(15)
            st.bar_chart(type_counts)

    # Tools and platforms
    st.header("Tools & Platforms")
    if "tools_and_platforms" in df_filtered.columns:
        all_tools = []
        for tools in df_filtered["tools_and_platforms"].dropna():
            if isinstance(tools, list):
                all_tools.extend(t.strip() for t in tools)
        if all_tools:
            tool_counts = pd.Series(all_tools).value_counts().head(15)
            st.bar_chart(tool_counts)

    # Policy summary
    st.header("Policy Summary")
    col1, col2, col3 = st.columns(3)
    if "has_final_exam" in df_filtered.columns:
        final_pct = df_filtered["has_final_exam"].dropna().mean() * 100
        col1.metric("% with Final Exam", f"{final_pct:.0f}%")
    if "has_group_work" in df_filtered.columns:
        group_pct = df_filtered["has_group_work"].dropna().mean() * 100
        col2.metric("% with Group Work", f"{group_pct:.0f}%")
    if "attendance_mandatory" in df_filtered.columns:
        attend_pct = df_filtered["attendance_mandatory"].dropna().mean() * 100
        col3.metric("% Mandatory Attendance", f"{attend_pct:.0f}%")

    # Raw data table
    st.header("Raw Data")
    display_cols = [c for c in ["department", "course_number", "course_title", "credits", "instructor", "semester", "has_final_exam", "has_group_work"] if c in df_filtered.columns]
    st.dataframe(df_filtered[display_cols], use_container_width=True)


if __name__ == "__main__":
    main()
