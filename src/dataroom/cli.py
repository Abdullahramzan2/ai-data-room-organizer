"""Command-line interface for Milestone 1 ingestion."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import click
from tqdm import tqdm

from dataroom.config import load_app_config, load_taxonomy
from dataroom.ingestion.extractors.legacy_office import LegacyOfficeConfig
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
