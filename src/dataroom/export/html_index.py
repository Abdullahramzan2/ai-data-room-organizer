"""Build searchable static HTML index from manifest rows."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

INDEX_LINK_MODES = frozenset({"original", "organized", "relative"})


def path_to_file_url(path: str) -> str:
    """Convert a local filesystem path to a file:// URL."""
    if not path:
        return ""
    normalized = path.replace("\\", "/")
    if normalized.startswith("//"):
        # UNC path: //server/share/...
        return "file:" + quote(normalized, safe="/:")
    return Path(path).expanduser().resolve().as_uri()


def resolve_link_target(
    row: dict[str, str],
    link_mode: str,
    output_dir: Path,
) -> str:
    """Pick the filesystem path used for index links."""
    mode = link_mode if link_mode in INDEX_LINK_MODES else "original"
    original = row.get("original_path", "")
    organized = row.get("output_path", "")

    if mode == "organized":
        return organized or original
    if mode == "relative":
        target = organized or original
        if not target:
            return ""
        target_path = Path(target)
        try:
            rel = target_path.relative_to(output_dir.resolve())
            return rel.as_posix()
        except ValueError:
            return target
    return original


def build_index_entries(
    manifest_rows: list[dict[str, str]],
    *,
    link_mode: str,
    output_dir: Path,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for row in manifest_rows:
        link_path = resolve_link_target(row, link_mode, output_dir)
        if link_mode == "relative":
            link_url = link_path
        else:
            link_url = path_to_file_url(link_path) if link_path else ""

        file_name = row.get("file_name", "")
        extension = Path(file_name).suffix.lower()
        entries.append(
            {
                "file_name": file_name,
                "category_folder": row.get("category_folder", ""),
                "confidence": row.get("confidence", ""),
                "score": float(row.get("score") or 0),
                "extension": extension,
                "modified_at": row.get("modified_at", ""),
                "link_url": link_url,
                "classification_reason": row.get("classification_reason", ""),
                "needs_review": row.get("needs_review", "false") == "true",
                "original_path": row.get("original_path", ""),
                "output_path": row.get("output_path", ""),
            }
        )
    return entries


def _render_html(entries: list[dict[str, Any]], *, title: str, link_mode: str) -> str:
    data_json = json.dumps(entries, ensure_ascii=False)
    safe_title = html.escape(title)
    safe_mode = html.escape(link_mode)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #1f2937; }}
    h1 {{ margin-bottom: 8px; }}
    .meta {{ color: #6b7280; margin-bottom: 20px; }}
    .filters {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px; }}
    label {{ display: block; font-size: 12px; color: #4b5563; margin-bottom: 4px; }}
    input, select {{ width: 100%; box-sizing: border-box; padding: 8px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ cursor: pointer; background: #f9fafb; position: sticky; top: 0; }}
    tr:hover {{ background: #f3f4f6; }}
    .review {{ color: #b45309; font-weight: 600; }}
    .count {{ margin: 12px 0; color: #374151; }}
    a {{ color: #1d4ed8; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>{safe_title}</h1>
  <div class="meta">Link mode: {safe_mode} | Open locally in your browser. No server required.</div>
  <div class="filters">
    <div>
      <label for="search">Search</label>
      <input id="search" type="search" placeholder="File name, category, reason...">
    </div>
    <div>
      <label for="category">Category</label>
      <select id="category"><option value="">All categories</option></select>
    </div>
    <div>
      <label for="extension">File type</label>
      <select id="extension"><option value="">All types</option></select>
    </div>
    <div>
      <label for="confidence">Confidence</label>
      <select id="confidence"><option value="">All levels</option></select>
    </div>
    <div>
      <label for="dateFrom">Modified from</label>
      <input id="dateFrom" type="date">
    </div>
    <div>
      <label for="dateTo">Modified to</label>
      <input id="dateTo" type="date">
    </div>
  </div>
  <div class="count" id="count"></div>
  <table>
    <thead>
      <tr>
        <th data-key="file_name">File</th>
        <th data-key="category_folder">Category</th>
        <th data-key="confidence">Confidence</th>
        <th data-key="score">Score</th>
        <th data-key="extension">Type</th>
        <th data-key="modified_at">Modified</th>
        <th>Reason</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>
  <script>
    const entries = {data_json};
    let sortKey = "file_name";
    let sortAsc = true;

    function uniqueValues(key) {{
      return [...new Set(entries.map(e => e[key]).filter(Boolean))].sort();
    }}

    function fillSelect(id, values) {{
      const select = document.getElementById(id);
      for (const value of values) {{
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      }}
    }}

    fillSelect("category", uniqueValues("category_folder"));
    fillSelect("extension", uniqueValues("extension"));
    fillSelect("confidence", uniqueValues("confidence"));

    function entryDate(value) {{
      if (!value) return null;
      const d = new Date(value);
      return Number.isNaN(d.getTime()) ? null : d;
    }}

    function matches(entry) {{
      const q = document.getElementById("search").value.trim().toLowerCase();
      const category = document.getElementById("category").value;
      const extension = document.getElementById("extension").value;
      const confidence = document.getElementById("confidence").value;
      const dateFrom = document.getElementById("dateFrom").value;
      const dateTo = document.getElementById("dateTo").value;

      if (category && entry.category_folder !== category) return false;
      if (extension && entry.extension !== extension) return false;
      if (confidence && entry.confidence !== confidence) return false;

      if (dateFrom || dateTo) {{
        const modified = entryDate(entry.modified_at);
        if (!modified) return false;
        if (dateFrom && modified < new Date(dateFrom)) return false;
        if (dateTo && modified > new Date(dateTo + "T23:59:59")) return false;
      }}

      if (!q) return true;
      const haystack = [
        entry.file_name,
        entry.category_folder,
        entry.classification_reason,
        entry.original_path,
        entry.output_path
      ].join(" ").toLowerCase();
      return haystack.includes(q);
    }}

    function render() {{
      const filtered = entries.filter(matches).sort((a, b) => {{
        const left = a[sortKey];
        const right = b[sortKey];
        if (typeof left === "number" && typeof right === "number") {{
          return sortAsc ? left - right : right - left;
        }}
        return sortAsc
          ? String(left).localeCompare(String(right))
          : String(right).localeCompare(String(left));
      }});

      const tbody = document.getElementById("rows");
      tbody.innerHTML = "";
      for (const entry of filtered) {{
        const tr = document.createElement("tr");
        const nameCell = document.createElement("td");
        if (entry.link_url) {{
          const link = document.createElement("a");
          link.href = entry.link_url;
          link.textContent = entry.file_name;
          if (entry.needs_review) link.className = "review";
          nameCell.appendChild(link);
        }} else {{
          nameCell.textContent = entry.file_name;
        }}
        tr.appendChild(nameCell);
        tr.appendChild(cell(entry.category_folder));
        tr.appendChild(cell(entry.confidence));
        tr.appendChild(cell(entry.score.toFixed ? entry.score.toFixed(2) : entry.score));
        tr.appendChild(cell(entry.extension));
        tr.appendChild(cell(entry.modified_at ? entry.modified_at.slice(0, 10) : ""));
        tr.appendChild(cell(entry.classification_reason));
        tbody.appendChild(tr);
      }}
      document.getElementById("count").textContent = `Showing ${{filtered.length}} of ${{entries.length}} files`;
    }}

    function cell(text) {{
      const td = document.createElement("td");
      td.textContent = text || "";
      return td;
    }}

    for (const id of ["search", "category", "extension", "confidence", "dateFrom", "dateTo"]) {{
      document.getElementById(id).addEventListener("input", render);
      document.getElementById(id).addEventListener("change", render);
    }}

    for (const th of document.querySelectorAll("th[data-key]")) {{
      th.addEventListener("click", () => {{
        const key = th.dataset.key;
        if (sortKey === key) sortAsc = !sortAsc;
        else {{ sortKey = key; sortAsc = true; }}
        render();
      }});
    }}

    render();
  </script>
</body>
</html>
"""


def write_html_index(
    path: Path,
    manifest_rows: list[dict[str, str]],
    *,
    link_mode: str = "original",
    output_dir: Path | None = None,
    title: str = "Data Room Index",
) -> None:
    """Write a standalone searchable HTML index."""
    base_dir = output_dir or path.parent
    entries = build_index_entries(manifest_rows, link_mode=link_mode, output_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _render_html(entries, title=title, link_mode=link_mode),
        encoding="utf-8",
    )
