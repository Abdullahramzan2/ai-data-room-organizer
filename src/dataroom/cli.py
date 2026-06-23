"""Command-line interface for the data room organizer."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import click
from tqdm import tqdm

from dataroom.classification import ClassificationEngine
from dataroom.classification.engine import default_cache_dir
from dataroom.classification.runtime import build_classification_runtime
from dataroom.config import load_app_config, load_taxonomy
from dataroom.export import (
    build_manifest_rows,
    write_html_index,
    write_manifest_csv,
    write_manifest_xlsx,
    write_review_queue_csv,
)
from dataroom.organizer import organize_files
from dataroom.pipeline import run_pipeline, run_rerun
from dataroom.pipeline.rerun import RerunError
from dataroom.doctor import run_doctor
from dataroom.doctor.checks import format_doctor_report
from dataroom.ingestion.extractors.legacy_office import LegacyOfficeConfig
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata
from dataroom.ingestion.pipeline import run_ingestion
from dataroom.ocr.tesseract import OcrConfig


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def main(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


@main.command("ingest")
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to application config YAML.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write extraction results as JSON (default: stdout summary).",
)
@click.option("--no-ocr", is_flag=True, help="Disable OCR even if configured.")
@click.option("--no-recursive", is_flag=True, help="Do not scan subfolders.")
def ingest_cmd(
    input_dir: Path,
    config_path: Path | None,
    output_path: Path | None,
    no_ocr: bool,
    no_recursive: bool,
) -> None:
    """Scan a folder and extract text/metadata from supported files."""
    config = load_app_config(config_path)
    input_cfg = config.get("input", {})
    ocr_cfg = config.get("ocr", {})
    ingest_cfg = config.get("ingestion", {})
    legacy_cfg = config.get("legacy_office", {})

    ocr_config = OcrConfig(
        enabled=not no_ocr and ocr_cfg.get("enabled", True),
        language=ocr_cfg.get("language", "eng"),
        pdf_dpi=ocr_cfg.get("pdf_dpi", 300),
        min_native_text_chars=ocr_cfg.get("min_native_text_chars", 50),
        tesseract_cmd=ocr_cfg.get("tesseract_cmd"),
        poppler_path=ocr_cfg.get("poppler_path"),
    )
    legacy_office_config = LegacyOfficeConfig(
        libreoffice_cmd=legacy_cfg.get("libreoffice_cmd"),
        enable_com=legacy_cfg.get("enable_com", True),
        conversion_timeout=legacy_cfg.get("conversion_timeout", 120),
    )

    def on_progress(current: int, total: int, path: Path) -> None:
        tqdm.write(f"[{current}/{total}] {path.name}")

    with tqdm(desc="Ingesting", unit="file") as bar:
        def progress(i: int, t: int, p: Path) -> None:
            on_progress(i, t, p)
            bar.update(1)

        result = run_ingestion(
            input_dir,
            supported_extensions=input_cfg.get("supported_extensions", []),
            recursive=not no_recursive and input_cfg.get("recursive", True),
            ocr_config=ocr_config,
            legacy_office_config=legacy_office_config,
            max_file_size_bytes=ingest_cfg.get("max_file_size_bytes", 0),
            max_text_chars=ingest_cfg.get("max_text_chars", 500_000),
            on_progress=progress,
        )

    summary = {
        "input_dir": str(input_dir),
        "processed": result.total_processed,
        "with_text": result.total_with_text,
        "skipped": len(result.skipped_files),
        "failed": len(result.failed_files),
        "documents": [d.to_dict() for d in result.documents],
        "skipped_files": [str(p) for p in result.skipped_files],
        "failed_files": [{"path": str(p), "error": e} for p, e in result.failed_files],
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        click.echo(f"Wrote results to {output_path}")
    else:
        click.echo(
            f"Processed {result.total_processed} files "
            f"({result.total_with_text} with text, "
            f"{len(result.skipped_files)} skipped, "
            f"{len(result.failed_files)} failed)"
        )


def _document_from_ingestion_row(row: dict[str, Any]) -> ExtractedDocument:
    return ExtractedDocument(
        metadata=FileMetadata(
            source_path=Path(row["source_path"]),
            file_name=row["file_name"],
            extension=row["extension"],
            file_size=row["file_size"],
        ),
        text_content=row.get("text_content", ""),
        ocr_text=row.get("ocr_text", ""),
        extraction_method=ExtractionMethod(row.get("extraction_method", "skipped")),
        extra=row.get("extra") or {},
    )


@main.command("classify")
@click.argument(
    "ingestion_json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to application config YAML.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write classification results as JSON (default: print summary).",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Optional output directory for audit log (same as pipeline run).",
)
def classify_cmd(
    ingestion_json: Path,
    config_path: Path | None,
    output_path: Path | None,
    output_dir: Path | None,
) -> None:
    """Classify documents from a dataroom ingest JSON file."""
    config = load_app_config(config_path)
    data = json.loads(ingestion_json.read_text(encoding="utf-8"))
    documents = [_document_from_ingestion_row(row) for row in data.get("documents", [])]

    if not documents:
        click.echo("No documents found in ingestion JSON.")
        return

    settings, guardrails, reasoning_provider, classification_config = build_classification_runtime(
        config,
        output_dir=output_dir,
    )
    engine = ClassificationEngine(
        load_taxonomy(config=config),
        classification_config,
        cache_dir=default_cache_dir(config),
        settings=settings,
        reasoning_provider=reasoning_provider,
        guardrails=guardrails,
    )

    results = []
    for doc in tqdm(documents, desc="Classifying", unit="file"):
        result = engine.classify_document(doc)
        results.append(result.to_dict())
        click.echo(
            f"{doc.metadata.file_name} -> {result.category_folder} "
            f"({result.confidence}, {result.score:.2f})"
        )

    summary = {
        "ingestion_json": str(ingestion_json),
        "classified": len(results),
        "results": results,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        click.echo(f"Wrote results to {output_path}")


@main.command("organize")
@click.argument(
    "classification_json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="Folder where taxonomy subfolders and copied files are written.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to application config YAML.",
)
@click.option("--rename", is_flag=True, help="Use standardized destination file names.")
def organize_cmd(
    classification_json: Path,
    output_dir: Path,
    config_path: Path | None,
    rename: bool,
) -> None:
    """Copy classified files into taxonomy folders (originals untouched)."""
    config = load_app_config(config_path)
    taxonomy = load_taxonomy(config=config)
    data = json.loads(classification_json.read_text(encoding="utf-8"))
    rows = data.get("results", [])
    if not rows:
        click.echo("No classification results found in JSON.")
        return

    organized = organize_files(rows, output_dir, taxonomy, rename=rename)
    for item in organized:
        click.echo(f"{item.source_path.name} -> {item.dest_path}")
    click.echo(f"Copied {len(organized)} file(s) to {output_dir}")


@main.command("run")
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="Output folder for organized files, manifest, and review queue.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to application config YAML.",
)
@click.option("--rename", is_flag=True, help="Use standardized destination file names.")
@click.option("--no-ocr", is_flag=True, help="Disable OCR even if configured.")
@click.option("--no-recursive", is_flag=True, help="Do not scan subfolders.")
def run_cmd(
    input_dir: Path,
    output_dir: Path,
    config_path: Path | None,
    rename: bool,
    no_ocr: bool,
    no_recursive: bool,
) -> None:
    """Ingest, classify, organize, and export in one step."""
    summary = run_pipeline(
        input_dir,
        output_dir,
        config_path=config_path,
        rename=rename,
        no_ocr=no_ocr,
        no_recursive=no_recursive,
    )
    click.echo(f"Processed {summary['processed']} file(s)")
    click.echo(f"Organized {summary['organized']} file(s) -> {summary['output_dir']}")
    click.echo(f"Manifest: {summary['manifest']}")
    click.echo(f"Review queue: {summary['review_queue']} ({summary['review_queue_count']} flagged)")
    click.echo(f"Summary: {output_dir / 'run_summary.json'}")


@main.command("rerun")
@click.argument(
    "output_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to application config YAML.",
)
@click.option("--rename", is_flag=True, help="Use standardized destination file names.")
def rerun_cmd(
    output_dir: Path,
    config_path: Path | None,
    rename: bool,
) -> None:
    """Re-organize from cached ingestion/classification after review-queue corrections."""
    try:
        summary = run_rerun(output_dir, config_path=config_path, rename=rename)
    except RerunError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Rerun complete — {summary['corrections_applied']} correction(s) applied")
    click.echo(f"Organized {summary['organized']} file(s) -> {summary['output_dir']}")
    click.echo(f"Review queue: {summary['review_queue']} ({summary['review_queue_count']} flagged)")
    for warning in summary.get("correction_warnings", []):
        click.echo(f"Warning: {warning}")
    click.echo(f"Summary: {output_dir / 'run_summary.json'}")


@main.command("export")
@click.argument(
    "ingestion_json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "classification_json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="Folder where manifest.csv and review_queue.csv are written.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to application config YAML.",
)
@click.option("--rename", is_flag=True, help="Match output paths used with dataroom organize --rename.")
def export_cmd(
    ingestion_json: Path,
    classification_json: Path,
    output_dir: Path,
    config_path: Path | None,
    rename: bool,
) -> None:
    """Write manifest.csv and review_queue.csv from ingest + classification JSON."""
    config = load_app_config(config_path)
    output_cfg = config.get("output", {})
    ingestion = json.loads(ingestion_json.read_text(encoding="utf-8"))
    classification = json.loads(classification_json.read_text(encoding="utf-8"))

    rows = build_manifest_rows(
        ingestion.get("documents", []),
        classification.get("results", []),
        output_dir,
        rename=rename,
    )
    manifest_path = output_dir / output_cfg.get("manifest_file", "manifest.csv")
    manifest_xlsx_path = output_dir / output_cfg.get("manifest_xlsx_file", "manifest.xlsx")
    index_html_path = output_dir / output_cfg.get("index_html_file", "index.html")
    review_path = output_dir / output_cfg.get("review_queue_file", "review_queue.csv")

    write_manifest_csv(manifest_path, rows)
    write_manifest_xlsx(manifest_xlsx_path, rows)
    write_html_index(
        index_html_path,
        rows,
        link_mode=str(output_cfg.get("index_link_mode", "original")),
        output_dir=output_dir,
    )
    write_review_queue_csv(review_path, rows)
    review_count = sum(1 for r in rows if r.get("needs_review") == "true")
    click.echo(f"Wrote {manifest_path} ({len(rows)} rows)")
    click.echo(f"Wrote {manifest_xlsx_path}")
    click.echo(f"Wrote {index_html_path}")
    click.echo(f"Wrote {review_path} ({review_count} rows)")


@main.command("doctor")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to application config YAML.",
)
@click.option("--json", "as_json", is_flag=True, help="Print results as JSON.")
def doctor_cmd(config_path: Path | None, as_json: bool) -> None:
    """Verify Python, OCR tools, embedding model, and optional LLM endpoints."""
    report = run_doctor(config_path)
    if as_json:
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(format_doctor_report(report))
    if report.has_failures:
        raise SystemExit(1)


@main.command("ui")
@click.option("--port", default=8501, show_default=True, help="Streamlit server port.")
def ui_cmd(port: int) -> None:
    """Launch the optional Streamlit UI (requires pip install -e \".[ui]\")."""
    try:
        import streamlit.web.cli as stcli
    except ImportError as exc:
        raise click.ClickException('Install UI support: pip install -e ".[ui]"') from exc

    app_path = Path(__file__).resolve().parent / "ui" / "app.py"
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    stcli.main()


@main.command("taxonomy")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
)
def taxonomy_cmd(config_path: Path | None) -> None:
    """Print loaded taxonomy categories."""
    config = load_app_config(config_path)
    taxonomy = load_taxonomy(config=config)
    click.echo(f"Taxonomy: {taxonomy.get('name')} (v{taxonomy.get('version')})")
    for cat in taxonomy.get("categories", []):
        click.echo(f"  {cat.get('id')}: {cat.get('folder')}")


if __name__ == "__main__":
    main()
