#!/usr/bin/env python3
"""Verify the deposited public snapshot without third-party dependencies."""

import hashlib
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "2025-04-30"
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
EMAIL = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}"
)


def workbook_issues(path):
    issues = []
    with ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            issues.append(f"{path.name}: invalid ZIP member {bad}")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = [
                "".join(node.itertext()) for node in root.findall("s:si", NS)
            ]
        for member in archive.namelist():
            if member.endswith((".xml", ".rels")):
                content = archive.read(member).decode("utf-8")
                if EMAIL.search(content):
                    issues.append(f"{path.name}: email address remains in {member}")
            if not re.fullmatch(r"xl/worksheets/sheet\d+\.xml", member):
                continue
            root = ET.fromstring(archive.read(member))
            rows = root.findall("s:sheetData/s:row", NS)
            if not rows:
                continue
            email_columns = set()
            for cell in rows[0].findall("s:c", NS):
                value = cell.find("s:v", NS)
                text = value.text if value is not None else ""
                if cell.get("t") == "s" and text is not None:
                    text = strings[int(text)]
                elif cell.get("t") == "inlineStr":
                    text = "".join(cell.find("s:is", NS).itertext())
                if str(text).strip().lower() == "emails":
                    email_columns.add(re.sub(r"\d", "", cell.get("r", "")))
            for row in rows[1:]:
                for cell in row.findall("s:c", NS):
                    if re.sub(r"\d", "", cell.get("r", "")) in email_columns:
                        if any(cell.find("s:" + tag, NS) is not None for tag in ("v", "is", "f")):
                            issues.append(f"{path.name}: populated emails cell {cell.get('r')}")
    return issues


def main():
    manifest = json.loads((SNAPSHOT / "manifest.json").read_text())
    expected = {entry["path"]: entry for entry in manifest["files"]}
    issues = []
    actual = {
        str(path.relative_to(SNAPSHOT))
        for path in SNAPSHOT.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS"}
    }
    if actual != set(expected):
        issues.append(f"Inventory mismatch: missing={sorted(set(expected)-actual)}, extra={sorted(actual-set(expected))}")
    checksums = {}
    for line in (SNAPSHOT / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        checksums[name] = digest
    if checksums != {name: entry["published_sha256"] for name, entry in expected.items()}:
        issues.append("SHA256SUMS differs from manifest")
    for name, entry in expected.items():
        path = SNAPSHOT / name
        if not path.is_file():
            continue
        hasher = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        if digest != entry["published_sha256"] or path.stat().st_size != entry["published_bytes"]:
            issues.append(f"Checksum or size mismatch: {name}")
        if path.suffix == ".xlsx":
            issues.extend(workbook_issues(path))
        elif path.suffix in {".json", ".txt", ".bib"} and EMAIL.search(path.read_text()):
            issues.append(f"Email address remains in {name}")
    if (SNAPSHOT / "emails.txt").exists():
        issues.append("Excluded contact list is present")
    if issues:
        print("Verification failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print(f"Verified {len(expected)} archive-derived files in snapshot {manifest['snapshot_id']}.")
    print("Checksums, file sizes, inventory, and contact-email removal passed.")
    print("This verifies artifact integrity, not scientific validity or reproducibility of the original analysis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
