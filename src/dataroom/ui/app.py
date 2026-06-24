"""Streamlit application — run, review, taxonomy, doctor, outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from dataroom.config import load_app_config, load_taxonomy, resolve_project_root
from dataroom.export.review_queue import (
    REVIEW_COLUMNS,
    ReviewQueueWriteError,
    read_review_queue_csv,
    write_review_queue_rows,
)
from dataroom.ui.helpers import (
    default_config_path,
    list_output_artifacts,
    load_duplicate_report_rows,
    load_pipeline_progress,
    load_run_summary,
    review_queue_path,
    taxonomy_folder_names,
)
from dataroom.ui.doctor_display import display_doctor_report
from dataroom.ui.outputs_display import (
    display_admin_mirror_panel,
    display_audit_log_hint,
    display_manifest_preview,
    display_processing_log_panel,
)
from dataroom.ui.summary_display import display_run_summary
from dataroom.ui.progress_display import LiveProgressPanel, render_duplicate_pairs_table, render_file_results_table
from dataroom.ui.widgets import folder_path_field

st.set_page_config(
    page_title="Data Room Organizer",
    page_icon="📁",
    layout="wide",
)


def _init_session_state() -> None:
    root = resolve_project_root()
    if "output_dir" not in st.session_state:
        st.session_state.output_dir = str(root / "output")
    if "input_dir" not in st.session_state:
        st.session_state.input_dir = str(root / "data")


def _config_path() -> Path:
    return default_config_path()


def _sidebar() -> str:
    st.sidebar.title("Data Room Organizer")
    st.sidebar.caption("Config")
    st.sidebar.code(str(_config_path()), language=None)

    folder_path_field("Input folder", "input_dir", sidebar=True, stacked=True)
    folder_path_field("Output directory", "output_dir", sidebar=True, stacked=True)

    return st.sidebar.radio(
        "Navigation",
        ["Run", "Review", "Taxonomy", "Doctor", "Outputs"],
        label_visibility="collapsed",
    )


def _page_run() -> None:
    st.header("Run pipeline")
    st.caption(
        "Ingest, classify, organize, and export in one step. Original files are never modified. "
        "Exports include manifest, HTML index, review queue, duplicate report, classification log, "
        "processing log, and admin mirror in `00_Admin_and_Index/`."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        rename = st.checkbox("Rename files", value=False, help=(
            "Standardized names: YYYY-MM-DD__Category__Source__Desc__OriginalName.ext "
            "(segments omitted when unknown)."
        ))
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

        panel = LiveProgressPanel()
        panel.update(None, force=True)

        try:
            from dataroom.ui.pipeline_runner import PipelineSubprocessError, run_pipeline_subprocess

            result = run_pipeline_subprocess(
                input_path,
                output_path,
                config_path=config_path,
                rename=rename,
                no_ocr=no_ocr,
                no_recursive=no_recursive,
                on_progress=lambda snap: panel.update(snap),
            )
        except PipelineSubprocessError as exc:
            st.error(str(exc))
            return
        except Exception as exc:
            st.error(f"Pipeline failed: {exc}")
            return

        final_progress = load_pipeline_progress(output_path, load_app_config(config_path))
        if final_progress:
            panel.update(final_progress, force=True)

        display_run_summary(result.summary, expanded=False)


def _save_review_queue(queue_path: Path, edited) -> bool:
    """Persist review queue edits; return True on success."""
    try:
        write_review_queue_rows(queue_path, edited.to_dict(orient="records"))
        return True
    except ReviewQueueWriteError as exc:
        st.error(str(exc))
        return False


def _page_review() -> None:
    st.header("Review queue")
    st.caption(
        "Set corrected_folder for flagged files (including duplicate pairs), save, then rerun without re-OCR."
    )

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

    duplicate_count = sum(
        1 for row in rows if "duplicate" in str(row.get("review_reason", "")).lower()
    )
    if duplicate_count:
        st.info(f"{duplicate_count} file(s) flagged for duplicate review.")

    rename_on_rerun = st.checkbox(
        "Rename files on rerun",
        value=False,
        help="Apply standardized rename when re-organizing copies.",
    )

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
        width="stretch",
    )

    col_save, col_rerun = st.columns(2)
    with col_save:
        if st.button("Save review queue"):
            if _save_review_queue(queue_path, edited):
                st.success(f"Saved {queue_path}")

    with col_rerun:
        if st.button("Rerun with corrections", type="primary"):
            if not _save_review_queue(queue_path, edited):
                return
            panel = LiveProgressPanel()
            panel.update(None, force=True)
            try:
                from dataroom.ui.pipeline_runner import PipelineSubprocessError, run_rerun_subprocess

                result = run_rerun_subprocess(
                    output_dir,
                    config_path=config_path,
                    rename=rename_on_rerun,
                    on_progress=lambda snap: panel.update(snap),
                )
            except PipelineSubprocessError as exc:
                st.error(str(exc))
                return
            except Exception as exc:
                st.error(f"Rerun failed: {exc}")
                return
            for warning in result.summary.get("correction_warnings", []):
                st.warning(warning)
            final_progress = load_pipeline_progress(output_dir, config)
            if final_progress:
                panel.update(final_progress, force=True)
            display_run_summary(result.summary, title="Rerun summary", expanded=False)


def _page_taxonomy() -> None:
    st.header("Taxonomy")
    taxonomy = load_taxonomy(config=load_app_config(_config_path()))

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
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _page_doctor() -> None:
    st.header("Environment check")
    st.caption("Verify Python, OCR tools, embedding model, and optional LLM endpoints.")

    if st.button("Run doctor", type="primary"):
        from dataroom.doctor import run_doctor

        with st.spinner("Checking environment…"):
            report = run_doctor(_config_path())
        display_doctor_report(report)
        if report.has_failures:
            st.error("One or more required checks failed.")
        else:
            st.success("No blocking failures detected.")


def _page_outputs() -> None:
    st.header("Outputs")
    st.caption(
        "Run summary, manifest preview, processing log, duplicate pairs, and artifact paths. "
        "Open `index.html` in a browser for searchable browsing with snippet and duplicate filters."
    )
    output_dir = Path(st.session_state.output_dir)
    config = load_app_config(_config_path())

    if not output_dir.is_dir():
        st.warning(f"Output directory not found: {output_dir}")
        return

    progress = load_pipeline_progress(output_dir, config)
    summary = load_run_summary(output_dir)
    if not progress and not summary:
        st.info("No pipeline outputs yet. Run the pipeline first.")
        return

    if summary:
        display_run_summary(summary, title="Run summary", expanded=True)

    if progress and progress.get("files"):
        st.subheader("File results")
        render_file_results_table(progress)

    dup_rows = progress.get("duplicate_pairs") if progress else []
    if not dup_rows:
        dup_rows = load_duplicate_report_rows(output_dir, config)
    if dup_rows:
        st.subheader(f"Duplicate pairs ({len(dup_rows)})")
        render_duplicate_pairs_table(dup_rows)

    display_manifest_preview(output_dir, config=config)
    if summary:
        display_processing_log_panel(output_dir, config=config, summary=summary)
        display_admin_mirror_panel(summary)

    artifacts = list_output_artifacts(output_dir, config=config)
    if artifacts:
        st.subheader("Output artifacts")
        st.dataframe(
            pd.DataFrame(artifacts),
            hide_index=True,
            width="stretch",
            height=min(420, 38 + len(artifacts) * 35),
        )

    index_path = output_dir / config.get("output", {}).get("index_html_file", "index.html")
    if index_path.is_file():
        st.markdown(f"**HTML index:** `{index_path}`")
        st.caption("Open in your browser — includes search, snippet column, and duplicate/review filters.")

    display_audit_log_hint(output_dir, config=config)


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
