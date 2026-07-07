"""Streamlit application — run, review, taxonomy, doctor, outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from dataroom.config import load_app_config, load_taxonomy, resolve_project_root
from dataroom.paths import default_input_dir, default_output_dir
from dataroom.pipeline.progress import clear_run_progress
from dataroom.export.review_queue import (
    REVIEW_COLUMNS,
    ReviewQueueWriteError,
    read_review_queue,
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
from dataroom.export.admin_outputs import resolve_artifact_path
from dataroom.ui.doctor_display import display_doctor_report
from dataroom.ui.outputs_display import (
    display_admin_mirror_panel,
    display_audit_log_hint,
    display_manifest_preview,
    display_processing_log_panel,
)
from dataroom.ui.summary_display import display_run_summary
from dataroom.ui.progress_display import (
    get_live_progress_panel,
    get_run_status_slot,
    render_duplicate_pairs_table,
    render_file_results_table,
    render_run_progress_poll_fragment,
    reset_live_progress_panel,
    repaint_run_status,
    update_run_status,
)
from dataroom.ui.widgets import folder_path_field

st.set_page_config(
    page_title="Data Room Organizer",
    page_icon="📁",
    layout="wide",
)


def _init_session_state() -> None:
    if "output_dir" not in st.session_state:
        st.session_state.output_dir = str(default_output_dir())
    if "input_dir" not in st.session_state:
        st.session_state.input_dir = str(default_input_dir())
    if "pipeline_running" not in st.session_state:
        st.session_state.pipeline_running = False
    if "pipeline_start_pending" not in st.session_state:
        st.session_state.pipeline_start_pending = False


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


def _review_queue_summary_lines(rows: list[dict[str, str]]) -> list[str]:
    """Human-readable breakdown of why files are in the review queue."""
    total = len(rows)
    if total == 0:
        return []

    duplicate = 0
    low_confidence = 0
    medium_confidence = 0
    ingestion_failed = 0
    other = 0
    for row in rows:
        reason = str(row.get("review_reason", "")).lower()
        if reason.startswith("ingestion failed"):
            ingestion_failed += 1
        elif "duplicate" in reason:
            duplicate += 1
        elif reason.startswith("low confidence") or "low confidence (" in reason:
            low_confidence += 1
        elif reason.startswith("medium confidence") or "medium confidence (" in reason:
            medium_confidence += 1
        else:
            other += 1

    lines = [f"{total} file(s) in the review queue."]
    if ingestion_failed:
        lines.append(f"{ingestion_failed} flagged for ingestion failure.")
    if duplicate:
        lines.append(f"{duplicate} flagged for duplicate review.")
    if low_confidence:
        lines.append(f"{low_confidence} flagged for low confidence.")
    if medium_confidence:
        lines.append(f"{medium_confidence} flagged for medium confidence.")
    if other:
        lines.append(f"{other} flagged for other review reasons.")
    return lines


def _page_run() -> None:
    st.header("Run pipeline")
    st.caption(
        "Ingest, classify, organize, and export in one step. Original files are never modified. "
        "Exports appear in the output folder only after the run **fully completes** (organize + export). "
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

    output_path = Path(st.session_state.output_dir)
    config_path = _config_path()
    config = load_app_config(config_path)
    input_path = Path(st.session_state.input_dir)

    run_clicked = st.button(
        "Run pipeline",
        type="primary",
        disabled=st.session_state.pipeline_running,
    )

    get_run_status_slot()
    if st.session_state.pipeline_running:
        if not st.session_state.get("_run_status_message"):
            update_run_status(None, starting=True, force=True)
        else:
            repaint_run_status()
    else:
        repaint_run_status()

    if run_clicked and not st.session_state.pipeline_running:
        if not input_path.is_dir():
            st.error(f"Input folder not found: {input_path}")
        else:
            clear_run_progress(output_path, config)
            reset_live_progress_panel(output_path)
            get_run_status_slot()
            st.session_state.pop("_live_run_final_snapshot", None)
            st.session_state.pop("_run_seen_progress", None)
            st.session_state.pop("_run_status_message", None)
            st.session_state.pop("run_page_error", None)
            st.session_state.pipeline_running = True
            st.session_state.pipeline_start_pending = True
            st.session_state.pipeline_run_options = {
                "rename": rename,
                "no_ocr": no_ocr,
                "no_recursive": no_recursive,
            }
            update_run_status(None, starting=True, force=True)
            st.rerun()

    if st.session_state.get("pipeline_start_pending"):
        st.session_state.pipeline_start_pending = False
        opts = st.session_state.get("pipeline_run_options", {})
        from dataroom.ui.pipeline_runner import start_pipeline_job

        start_pipeline_job(
            input_path,
            output_path,
            config_path=config_path,
            rename=bool(opts.get("rename")),
            no_ocr=bool(opts.get("no_ocr")),
            no_recursive=bool(opts.get("no_recursive")),
        )
        update_run_status(None, starting=True, force=True)

    render_run_progress_poll_fragment(output_path, config)

    if not st.session_state.pipeline_running:
        panel = get_live_progress_panel(output_path)
        progress = st.session_state.get("_live_run_final_snapshot")
        if progress is None:
            progress = load_pipeline_progress(output_path, config)
        if progress:
            if not st.session_state.get("_run_status_message"):
                update_run_status(progress, force=True)
            panel.update(progress, force=True)

    if st.session_state.get("run_page_error"):
        st.error(st.session_state["run_page_error"])


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
        "Set corrected folder for flagged files (including duplicate pairs), save, then rerun without re-OCR."
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

    rows = read_review_queue(queue_path)
    if not rows:
        st.success("Review queue is empty — no files need review.")
        return

    summary_lines = _review_queue_summary_lines(rows)
    if summary_lines:
        st.info("\n\n".join(summary_lines))

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
        if st.button(
            "Rerun with corrections",
            type="primary",
            disabled=st.session_state.pipeline_running,
        ):
            if not _save_review_queue(queue_path, edited):
                pass
            else:
                panel = get_live_progress_panel(output_dir)
                reset_live_progress_panel(output_dir)
                panel = get_live_progress_panel(output_dir)
                panel.clear()
                st.session_state.pipeline_running = True
                update_run_status(None, starting=True)
                try:
                    from dataroom.ui.pipeline_runner import PipelineSubprocessError, run_rerun_subprocess

                    def on_progress(snapshot: dict) -> None:
                        update_run_status(snapshot)
                        panel.update(snapshot)

                    result = run_rerun_subprocess(
                        output_dir,
                        config_path=config_path,
                        rename=rename_on_rerun,
                        on_progress=on_progress,
                    )
                    for warning in result.summary.get("correction_warnings", []):
                        st.warning(warning)
                    display_run_summary(result.summary, title="Rerun summary", expanded=False)
                except PipelineSubprocessError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Rerun failed: {exc}")
                finally:
                    st.session_state.pipeline_running = False


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

    index_path = resolve_artifact_path(
        output_dir,
        config,
        summary_key="index_html",
        default_name=str(config.get("output", {}).get("index_html_file", "index.html")),
        summary=summary,
    )
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
