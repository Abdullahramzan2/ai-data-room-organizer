"""Streamlit application — run, review, taxonomy, doctor, outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from dataroom.config import load_app_config, load_taxonomy, resolve_project_root
from dataroom.export.review_queue import REVIEW_COLUMNS, read_review_queue_csv, write_review_queue_rows
from dataroom.ui.helpers import (
    default_config_path,
    list_output_artifacts,
    load_run_summary,
    review_queue_path,
    taxonomy_folder_names,
)
from dataroom.ui.widgets import folder_path_field

st.set_page_config(
    page_title="Data Room Organizer",
    page_icon="📁",
    layout="wide",
)


def _init_session_state() -> None:
    root = resolve_project_root()
    if "config_path" not in st.session_state:
        st.session_state.config_path = str(default_config_path())
    if "output_dir" not in st.session_state:
        st.session_state.output_dir = str(root / "output")
    if "input_dir" not in st.session_state:
        st.session_state.input_dir = str(root / "data")


def _config_path() -> Path | None:
    raw = st.session_state.get("config_path", "").strip()
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_file() else None


def _sidebar() -> str:
    st.sidebar.title("Data Room Organizer")
    st.sidebar.text_input("Config YAML", key="config_path")
    folder_path_field("Output directory", "output_dir", sidebar=True)
    return st.sidebar.radio(
        "Navigation",
        ["Run", "Review", "Taxonomy", "Doctor", "Outputs"],
        label_visibility="collapsed",
    )


def _page_run() -> None:
    st.header("Run pipeline")
    st.caption("Ingest, classify, organize, and export in one step. Original files are never modified.")

    folder_path_field("Input folder", "input_dir")
    col1, col2, col3 = st.columns(3)
    with col1:
        rename = st.checkbox("Rename files", value=False)
    with col2:
        no_ocr = st.checkbox("Disable OCR", value=False)
    with col3:
        no_recursive = st.checkbox("Non-recursive scan", value=False)

    if st.button("Run pipeline", type="primary"):
        input_path = Path(st.session_state.input_dir)
        output_path = Path(st.session_state.output_dir)
        config_path = _config_path()
        if not input_path.is_dir():
            st.error(f"Input folder not found: {input_path}")
            return

        with st.spinner("Running pipeline in background process…"):
            try:
                from dataroom.ui.pipeline_runner import PipelineSubprocessError, run_pipeline_subprocess

                result = run_pipeline_subprocess(
                    input_path,
                    output_path,
                    config_path=config_path,
                    rename=rename,
                    no_ocr=no_ocr,
                    no_recursive=no_recursive,
                )
            except PipelineSubprocessError as exc:
                st.error(str(exc))
                if exc.log:
                    with st.expander("Process log"):
                        st.code(exc.log)
                return
            except Exception as exc:
                st.error(f"Pipeline failed: {exc}")
                return

        summary = result.summary
        if result.log:
            with st.expander("Process log"):
                st.code(result.log)

        st.success(
            f"Processed {summary['processed']} file(s); "
            f"organized {summary['organized']}; "
            f"{summary['review_queue_count']} in review queue."
        )
        st.json(summary)


def _page_review() -> None:
    st.header("Review queue")
    st.caption("Set corrected_folder for flagged files, save, then rerun without re-OCR.")

    output_dir = Path(st.session_state.output_dir)
    config_path = _config_path()
    config = load_app_config(config_path)
    taxonomy = load_taxonomy(config=config)
    folders = taxonomy_folder_names(taxonomy)
    queue_path = review_queue_path(output_dir, config)

    if not queue_path.is_file():
        st.info(f"No review queue at {queue_path}. Run the pipeline first.")
        return

    rows = read_review_queue_csv(queue_path)
    if not rows:
        st.success("Review queue is empty — no files need review.")
        return

    df = pd.DataFrame(rows, columns=REVIEW_COLUMNS)
    folder_options = [""] + folders
    edited = st.data_editor(
        df,
        column_config={
            "corrected_folder": st.column_config.SelectboxColumn(
                "Corrected folder",
                options=folder_options,
                help="Taxonomy folder to use on rerun",
            ),
            "file_name": st.column_config.TextColumn(disabled=True),
            "original_path": st.column_config.TextColumn(disabled=True),
            "assigned_folder": st.column_config.TextColumn(disabled=True),
            "confidence": st.column_config.TextColumn(disabled=True),
            "score": st.column_config.TextColumn(disabled=True),
            "review_reason": st.column_config.TextColumn(disabled=True),
            "classification_reason": st.column_config.TextColumn(disabled=True),
            "supporting_terms": st.column_config.TextColumn(disabled=True),
        },
        hide_index=True,
        use_container_width=True,
    )

    col_save, col_rerun = st.columns(2)
    with col_save:
        if st.button("Save review queue"):
            write_review_queue_rows(queue_path, edited.to_dict(orient="records"))
            st.success(f"Saved {queue_path}")

    with col_rerun:
        if st.button("Rerun with corrections", type="primary"):
            write_review_queue_rows(queue_path, edited.to_dict(orient="records"))
            with st.spinner("Applying corrections in background process…"):
                try:
                    from dataroom.ui.pipeline_runner import PipelineSubprocessError, run_rerun_subprocess

                    result = run_rerun_subprocess(
                        output_dir,
                        config_path=config_path,
                    )
                except PipelineSubprocessError as exc:
                    st.error(str(exc))
                    if exc.log:
                        with st.expander("Process log"):
                            st.code(exc.log)
                    return
                except Exception as exc:
                    st.error(f"Rerun failed: {exc}")
                    return
            summary = result.summary
            if result.log:
                with st.expander("Process log"):
                    st.code(result.log)
            st.success(f"Applied {summary['corrections_applied']} correction(s).")
            for warning in summary.get("correction_warnings", []):
                st.warning(warning)
            st.json(summary)


def _page_taxonomy() -> None:
    st.header("Taxonomy")
    config_path = _config_path()
    taxonomy = load_taxonomy(config=load_app_config(config_path))

    st.subheader(f"{taxonomy.get('name', 'taxonomy')} (v{taxonomy.get('version', '?')})")
    st.write(taxonomy.get("description", ""))

    rows = []
    for cat in taxonomy.get("categories", []):
        keywords = cat.get("keywords") or []
        rows.append(
            {
                "id": cat.get("id", ""),
                "folder": cat.get("folder", ""),
                "description": str(cat.get("description", "")).strip().replace("\n", " ")[:120],
                "keywords": len(keywords),
                "review_queue": bool(cat.get("is_review_queue", False)),
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _page_doctor() -> None:
    st.header("Environment check")
    st.caption("Verify Python, OCR tools, embedding model, and optional LLM endpoints.")

    if st.button("Run doctor", type="primary"):
        from dataroom.doctor import run_doctor
        from dataroom.doctor.checks import format_doctor_report

        with st.spinner("Checking environment…"):
            report = run_doctor(_config_path())
        st.code(format_doctor_report(report))
        if report.has_failures:
            st.error("One or more required checks failed.")
        else:
            st.success("No blocking failures detected.")

        with st.expander("JSON report"):
            st.json(report.to_dict())


def _page_outputs() -> None:
    st.header("Outputs")
    output_dir = Path(st.session_state.output_dir)
    config_path = _config_path()
    config = load_app_config(config_path)

    if not output_dir.is_dir():
        st.warning(f"Output directory not found: {output_dir}")
        return

    summary = load_run_summary(output_dir)
    if summary:
        metrics = {
            "processed": summary.get("processed"),
            "organized": summary.get("organized"),
            "review_queue_count": summary.get("review_queue_count"),
            "duplicate_pair_count": summary.get("duplicate_pair_count"),
            "api_used_count": summary.get("api_used_count"),
            "rerun": summary.get("rerun", False),
            "corrections_applied": summary.get("corrections_applied", 0),
        }
        st.json(metrics)
    else:
        st.info("No run_summary.json yet. Run the pipeline first.")

    artifacts = list_output_artifacts(output_dir, config=config)
    st.dataframe(pd.DataFrame(artifacts), hide_index=True, use_container_width=True)

    index_path = output_dir / config.get("output", {}).get("index_html_file", "index.html")
    if index_path.is_file():
        st.markdown(f"**HTML index:** `{index_path}`")
        st.caption("Open index.html in a browser for searchable browsing (no server required).")


def main() -> None:
    _init_session_state()
    page = _sidebar()

    if page == "Run":
        _page_run()
    elif page == "Review":
        _page_review()
    elif page == "Taxonomy":
        _page_taxonomy()
    elif page == "Doctor":
        _page_doctor()
    elif page == "Outputs":
        _page_outputs()


if __name__ == "__main__":
    main()
