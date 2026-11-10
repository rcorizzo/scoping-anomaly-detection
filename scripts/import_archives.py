#!/usr/bin/env python3
"""Deposit author-supplied archives without unrelated data or contact lists."""

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile


EMAIL = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}"
)
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError(f"Unsafe archive path: {name}")
    return path


def clean_workbook(data):
    cleared = replacements = 0
    output = io.BytesIO()
    with ZipFile(io.BytesIO(data)) as source, ZipFile(output, "w") as target:
        strings = []
        if "xl/sharedStrings.xml" in source.namelist():
            root = ET.fromstring(source.read("xl/sharedStrings.xml"))
            strings = ["".join(n.itertext()) for n in root.findall("s:si", NS)]
        for info in source.infolist():
            content = source.read(info)
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", info.filename):
                root = ET.fromstring(content)
                rows = root.findall("s:sheetData/s:row", NS)
                columns = set()
                if rows:
                    for cell in rows[0].findall("s:c", NS):
                        value = cell.find("s:v", NS)
                        text = value.text if value is not None else ""
                        if cell.get("t") == "s" and text:
                            text = strings[int(text)]
                        elif cell.get("t") == "inlineStr":
                            text = "".join(cell.find("s:is", NS).itertext())
                        if str(text).strip().lower() == "emails":
                            columns.add(re.sub(r"\d", "", cell.get("r", "")))
                changed = False
                for row in rows[1:]:
                    for cell in row.findall("s:c", NS):
                        if re.sub(r"\d", "", cell.get("r", "")) not in columns:
                            continue
                        children = [cell.find("s:" + tag, NS) for tag in ("v", "is", "f")]
                        children = [child for child in children if child is not None]
                        if children:
                            for child in children:
                                cell.remove(child)
                            cell.attrib.pop("t", None)
                            cleared += 1
                            changed = True
                if changed:
                    content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            if info.filename.endswith((".xml", ".rels")):
                text, count = EMAIL.subn("[email redacted]", content.decode("utf-8"))
                replacements += count
                content = text.encode("utf-8")
            target.writestr(info, content)
    if not cleared and not replacements:
        return data, 0, 0
    return output.getvalue(), cleared, replacements


def entry(name, original, public, cleared=0, replacements=0):
    return {
        "path": name,
        "original_bytes": len(original),
        "published_bytes": len(public),
        "original_sha256": digest(original),
        "published_sha256": digest(public),
        "transformation": "contact-email removal" if original != public else "unchanged",
        "email_address_replacements": replacements,
        "email_column_cells_cleared": cleared,
    }


def write_manifest(folder, manifest):
    manifest["files"].sort(key=lambda x: x["path"])
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (folder / "SHA256SUMS").write_text("".join(
        f"{e['published_sha256']}  {e['path']}\n" for e in manifest["files"]
    ))


def import_results(archive, root):
    folder = root / "data" / "2026-03-09"
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {
        "snapshot_id": "2026-03-09", "prepared_on": "2026-11-09",
        "source_archive": archive.name,
        "source_archive_sha256": digest(archive.read_bytes()),
        "configured_year_start": "2016", "configured_year_end": "2025",
        "logged_processing_date": "2026-03-09", "logged_timezone": None,
        "scientific_validation_status": "Archived outputs; 11,079 relevant flags agree with the PRISMA export, not the manuscript total of 19,884. No search rerun or independent classification validation performed.",
        "excluded": [], "files": [],
    }
    with ZipFile(archive) as source:
        files = [i for i in source.infolist() if not i.is_dir()]
        manifest["source_archive_file_count"] = len(files)
        manifest["source_archive_extension_counts"] = dict(Counter(PurePosixPath(i.filename).suffix for i in files))
        for info in files:
            name = str(safe_name(info.filename))
            if name == "emails.txt":
                manifest["excluded"].append({"path": name, "reason": "Contact list excluded at the author's request"})
                continue
            original = source.read(info)
            public, cleared, replacements = original, 0, 0
            if name.endswith(".xlsx"):
                public, cleared, replacements = clean_workbook(original)
            elif name.endswith((".json", ".txt", ".bib")):
                text, replacements = EMAIL.subn("[email redacted]", original.decode("utf-8"))
                public = text.encode("utf-8")
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(public)
            manifest["files"].append(entry(name, original, public, cleared, replacements))
    manifest["published_archive_file_count"] = len(manifest["files"])
    write_manifest(folder, manifest)


def import_source(archive, root):
    folder = root / "toolkit"
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {
        "source_archive": archive.name,
        "source_archive_sha256": digest(archive.read_bytes()),
        "archive_revision_identifier": "65087b32ca5001c41726a67f00c3e5cee9ee47fe",
        "execution_commit_verified": False,
        "excluded": [], "files": [],
    }
    with ZipFile(archive) as source:
        files = [i for i in source.infolist() if not i.is_dir()]
        prefixes = {safe_name(i.filename).parts[0] for i in files}
        if len(prefixes) != 1:
            raise ValueError("Expected one enclosing source directory")
        manifest["source_archive_file_count"] = len(files)
        for info in files:
            parts = safe_name(info.filename).parts[1:]
            name = str(PurePosixPath(*parts))
            reason = None
            if parts[0] == "data":
                reason = "Unrelated review data omitted as requested"
            elif parts[0] in {"references", "mockups"}:
                reason = "Ancillary reference documents or mockup, not executable toolkit source"
            elif name == "dockerfile":
                if source.read(info) != source.read(next(iter(prefixes)) + "/Dockerfile"):
                    raise ValueError("Dockerfile case variants differ")
                reason = "Identical case-only duplicate of Dockerfile"
            elif name in {"emails.sh", "bash_scripts/setup_linux_git.sh"}:
                reason = "Ancillary contact-list collection or personal Git-setup utility"
            if reason:
                manifest["excluded"].append({"path": name, "reason": reason})
                continue
            content = source.read(info)
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            manifest["files"].append(entry(name, content, content))
    manifest["published_archive_file_count"] = len(manifest["files"])
    write_manifest(folder, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    import_source(args.source, args.destination)
    import_results(args.results, args.destination)
    print("Imported toolkit source and sanitized results; original archives were not modified.")


if __name__ == "__main__":
    main()
