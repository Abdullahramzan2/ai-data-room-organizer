from pathlib import Path

from dataroom.pipeline import run_pipeline


def test_run_pipeline(tmp_path: Path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "PSA_agreement.txt").write_text(
        "purchase and sale agreement PSA escrow closing conditions",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    summary = run_pipeline(input_dir, output_dir, no_ocr=True)

    assert summary["processed"] == 1
    assert summary["organized"] == 1
    assert (output_dir / "manifest.csv").is_file()
    assert (output_dir / "review_queue.csv").is_file()
    assert (output_dir / "run_summary.json").is_file()
    assert (input_dir / "PSA_agreement.txt").is_file()
