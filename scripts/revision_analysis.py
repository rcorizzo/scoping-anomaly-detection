#!/usr/bin/env python3
"""Reconstruct descriptive figures from one frozen retained-record tag table."""

import argparse
from collections import Counter
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform


ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    "Application Domain": ("application-domains", "Application domains"),
    "Data type": ("data-types", "Data types"),
    "AI models - Shallow": ("shallow-models", "Shallow model families"),
    "AI models - DL": ("deep-models", "Deep model families"),
    "Learning setting": ("learning-settings", "Learning settings"),
    "Supervision type": ("supervision-types", "Supervision terminology"),
    "Concerns": ("concerns", "Research and deployment concerns"),
}
SOURCE_COMMIT = "6673b471ef6903b4921b7ef90e7c2c88fff87655"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_tags(value):
    if value is None or value == "":
        return set()
    if not isinstance(value, str):
        raise ValueError(f"Expected semicolon-delimited text, got {type(value).__name__}")
    values = [item.strip() for item in value.split(";")]
    if any(not item for item in values):
        raise ValueError("Empty category token")
    return set(values)


def validate_records(records):
    if not records:
        raise ValueError("The retained-record cohort is empty")
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError("Missing or repeated snapshot record identifiers")
    if any(not 2016 <= record["year"] <= 2025 for record in records):
        raise ValueError("Publication year outside 2016--2025")


def summarize(records, dimensions, domain_dimension="Application Domain"):
    validate_records(records)
    years = sorted({record["year"] for record in records})
    categories = {group: sorted(set().union(*(r["tags"].get(group, set()) for r in records))) for group in dimensions}
    annual, coverage, cross = [], [], []
    for group in dimensions:
        for year in [*years, "All"]:
            subset = records if year == "All" else [r for r in records if r["year"] == year]
            tagged = sum(bool(r["tags"].get(group)) for r in subset)
            counts = Counter(tag for r in subset for tag in set(r["tags"].get(group, set())))
            assignments = sum(counts.values())
            coverage.append({"dimension": group, "year": year, "records": len(subset), "tagged": tagged,
                             "untagged": len(subset) - tagged, "coverage_pct": 100 * tagged / len(subset)})
            for category in categories[group]:
                count = counts[category]
                annual.append({"dimension": group, "year": year, "category": category, "count": count,
                               "records": len(subset), "assignments": assignments,
                               "prevalence_pct": 100 * count / len(subset),
                               "assignment_share_pct": 100 * count / assignments if assignments else None})
    if domain_dimension in dimensions:
        domains = categories[domain_dimension]
        for group in dimensions:
            if group == domain_dimension:
                continue
            for domain in domains:
                subset = [r for r in records if domain in r["tags"].get(domain_dimension, set())]
                assignments = sum(len(r["tags"].get(group, set())) for r in subset)
                for category in categories[group]:
                    count = sum(category in r["tags"].get(group, set()) for r in subset)
                    marginal = sum(category in r["tags"].get(group, set()) for r in records)
                    assert count <= min(len(subset), marginal)
                    cross.append({"dimension": group, "domain": domain, "category": category, "count": count,
                                  "domain_records": len(subset), "category_records": marginal,
                                  "within_domain_prevalence_pct": 100 * count / len(subset),
                                  "assignment_share_pct": 100 * count / assignments if assignments else None})
    return {"annual": annual, "coverage": coverage, "cross": cross, "categories": categories}


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def import_records(source, destination):
    import openpyxl

    configuration = json.loads((source.parent / "search_data_original.json").read_text())
    allowed = {g["property_group"]: {items[0] for items in g["synonyms"]} for g in configuration["properties"]}
    workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
    rows = workbook.active.values
    headers = next(rows)
    records, seen_links, seen_dois = [], set(), set()
    missing_dois = 0
    for row in rows:
        item = dict(zip(headers, row))
        if item["is_article_relevant"] is not True:
            continue
        tags = {group: parse_tags(item[group]) for group in GROUPS}
        for group, values in tags.items():
            if values - allowed[group]:
                raise ValueError(f"Unknown canonical labels in {group}")
        tags["Sources"] = parse_tags(item["all_sources"] or item["source"])
        # The identifier is stable within this export, not necessarily across runs.
        identity = hashlib.sha256(item["bibtex_id"].encode()).hexdigest()[:20]
        records.append({"id": identity, "year": int(item["year"]), "tags": tags})
        link = item["link"]
        if not link or link in seen_links:
            raise ValueError("Repeated or missing retained-record link")
        seen_links.add(link)
        if item["doi"]:
            doi = str(item["doi"]).strip().lower().removeprefix("https://doi.org/").removeprefix("http://dx.doi.org/")
            if doi in seen_dois:
                raise ValueError("Repeated retained-record DOI")
            seen_dois.add(doi)
        else:
            missing_dois += 1
    validate_records(records)
    if len(records) != 11079:
        raise ValueError(f"Expected 11,079 retained rows, found {len(records)}")
    result = summarize(records, [*GROUPS, "Sources"])
    archived = openpyxl.load_workbook(source.parent / "aggr_property_year.xlsx", read_only=True, data_only=True)
    expected = {(g, p, int(y)): int(n) for g, p, y, n in list(archived.active.values)[1:] if g in GROUPS}
    actual = {(r["dimension"], r["category"], r["year"]): r["count"] for r in result["annual"]
              if r["dimension"] in GROUPS and r["year"] != "All" and r["count"]}
    if expected != actual:
        raise ValueError("Record-derived annual counts differ from archived property-year counts")
    destination.mkdir(parents=True, exist_ok=True)
    export = [{"id": r["id"], "year": r["year"], **{g: ";".join(sorted(r["tags"][g])) for g in [*GROUPS, "Sources"]}} for r in records]
    write_csv(destination / "record_tags.csv", export)
    manifest = {
        "source_repository": "https://github.com/rcorizzo/scoping-anomaly-detection",
        "source_commit": SOURCE_COMMIT, "snapshot": "2026-03-09", "source_workbook": source.name,
        "source_workbook_sha256": sha256(source), "retained_rows": len(records),
        "missing_doi_rows": missing_dois, "repeated_nonmissing_doi": 0, "repeated_links": 0,
        "canonical_categories": {g: sorted(allowed[g]) for g in GROUPS},
        "annual_counts_match_archived_export": True,
        "record_table_sha256": sha256(destination / "record_tags.csv"),
        "counting_unit": "One retained export row; unique snapshot ID and link, no repeated nonmissing normalized DOI",
        "semantic_validation": "No new manual classification validation or risk-of-bias appraisal performed",
        "privacy": "Only hashed snapshot identifiers, years, and canonical category/source tags retained",
    }
    (destination / "input_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return records


def load_records(path):
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    records = [{"id": row["id"], "year": int(row["year"]),
                "tags": {g: parse_tags(row[g]) for g in [*GROUPS, "Sources"]}} for row in rows]
    validate_records(records)
    manifest = json.loads(path.with_name("input_manifest.json").read_text())
    if sha256(path) != manifest["record_table_sha256"] or len(records) != manifest["retained_rows"]:
        raise ValueError("Frozen input does not match its manifest")
    return records


def plotting_setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.titlesize": 11,
                         "axes.labelsize": 10, "xtick.labelsize": 9, "ytick.labelsize": 9,
                         "legend.fontsize": 9, "pdf.fonttype": 42, "ps.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False})
    return plt


def annual_plot(group, slug, title, result, output):
    import numpy as np
    from matplotlib.ticker import PercentFormatter, MaxNLocator
    plt = plotting_setup()
    categories = result["categories"][group]
    years = sorted({r["year"] for r in result["annual"] if r["year"] != "All"})
    rows = {(r["category"], r["year"]): r for r in result["annual"] if r["dimension"] == group}
    colors = [plt.get_cmap("tab10")(i) for i in range(len(categories))]
    fig, axes = plt.subplots(3, 1, figsize=(7.4, 8.4), sharex=True)
    fig.subplots_adjust(left=.12, right=.98, top=.95, bottom=.17, hspace=.32)
    for index, ax in enumerate(axes):
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#dddddd", linewidth=.6)
        ax.set_xticks(years)
        ax.tick_params(axis="x", labelbottom=True)
        ax.set_xlim(years[0] - .5, years[-1] + .5)
    axes[0].set_title(f"(a) {title}: absolute counts", loc="left", fontweight="bold")
    axes[1].set_title("(b) Prevalence among all retained records in each year", loc="left", fontweight="bold")
    axes[2].set_title("(c) Composition of tag assignments in each year", loc="left", fontweight="bold")
    bottom = np.zeros(len(years))
    handles = []
    for category, color in zip(categories, colors):
        counts = [rows[category, y]["count"] for y in years]
        prevalence = [rows[category, y]["prevalence_pct"] for y in years]
        shares = [rows[category, y]["assignment_share_pct"] or 0 for y in years]
        handle, = axes[0].plot(years, counts, color=color, marker="o", markersize=3, linewidth=1.4, label=category)
        handles.append(handle)
        axes[1].plot(years, prevalence, color=color, marker="o", markersize=3, linewidth=1.4)
        axes[2].bar(years, shares, bottom=bottom, width=.75, color=color, edgecolor="white", linewidth=.4)
        for y, share, base in zip(years, shares, bottom):
            if share >= 9:
                # High-contrast annotation only for segments large enough to read.
                luminance = .2126 * color[0] + .7152 * color[1] + .0722 * color[2]
                axes[2].text(y, base + share / 2, f"{share:.0f}", ha="center", va="center", fontsize=8,
                             color="white" if luminance < .58 else "black")
        bottom += np.array(shares)
    axes[0].set_ylabel("Records")
    axes[0].set_ylim(bottom=0)
    axes[0].yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    axes[1].set_ylabel("% of records")
    axes[1].set_ylim(bottom=0)
    axes[1].yaxis.set_major_formatter(PercentFormatter())
    axes[2].set_ylabel("% of assignments")
    axes[2].set_ylim(0, 100)
    axes[2].yaxis.set_major_formatter(PercentFormatter())
    axes[2].set_xlabel("Publication year")
    fig.legend(handles, categories, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(.53, .01))
    filename = output / f"annual-{slug}.pdf"
    fig.savefig(filename, metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(filename.with_suffix(".png"), dpi=150)
    plt.close(fig)


def cross_plot(group, slug, title, result, output):
    import numpy as np
    plt = plotting_setup()
    domains = result["categories"]["Application Domain"]
    categories = result["categories"][group]
    cells = {(r["domain"], r["category"]): r for r in result["cross"] if r["dimension"] == group}
    values = np.array([[cells[d, c]["within_domain_prevalence_pct"] for c in categories] for d in domains])
    fig, ax = plt.subplots(figsize=(7.4, 5.1))
    fig.subplots_adjust(left=.29, right=.86, bottom=.27, top=.93)
    image = ax.imshow(values, cmap="YlGnBu", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(categories)), categories, rotation=35, ha="right", fontsize=11)
    ax.set_yticks(range(len(domains)), [f"{d}\n(n={cells[d,categories[0]]['domain_records']:,})" for d in domains], fontsize=11)
    ax.set_title(title, loc="left", fontsize=12.5, fontweight="bold")
    for i, domain in enumerate(domains):
        for j, category in enumerate(categories):
            cell = cells[domain, category]
            ax.text(j, i, f"{cell['count']}\n{cell['within_domain_prevalence_pct']:.1f}%", ha="center", va="center",
                    fontsize=11.5, color="white" if values[i,j] > 55 else "black")
    fig.colorbar(image, ax=ax, fraction=.045, pad=.03, label="% of all retained records in domain")
    name = output / f"cross-domain-{slug}.pdf"
    fig.savefig(name, metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(name.with_suffix(".png"), dpi=150)
    plt.close(fig)


def export_analysis(records, data, figures):
    figures.mkdir(parents=True, exist_ok=True)
    result = summarize(records, [*GROUPS, "Sources"])
    for name in ["annual", "coverage", "cross"]:
        write_csv(data / f"{name}.csv", result[name])
    for group, (slug, title) in GROUPS.items():
        annual_plot(group, slug, title, result, figures)
    for group in ["AI models - DL", "Data type", "Concerns"]:
        slug, title = GROUPS[group]
        cross_plot(group, slug, title, result, figures)
    annual_plot("Sources", "sources", "Source attributions", result, figures)
    generate_tex(result, data)
    manifest = {
        "input_sha256": sha256(data / "record_tags.csv"), "records": len(records),
        "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in ["matplotlib", "numpy", "openpyxl"]},
        "script_sha256": sha256(Path(__file__)),
        "files": [{"path": p.name, "sha256": sha256(p)} for p in sorted(figures.glob("*.pdf"))],
        "tables": [{"path": p.name, "sha256": sha256(p)} for p in sorted(data.iterdir())
                   if p.suffix in {".csv", ".tex"}],
        "inference": "Descriptive summaries only; no hypothesis tests or confidence intervals",
    }
    (data / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"records": len(records), "coverage": [r for r in result["coverage"] if r["year"] == "All"]}, indent=2))


def tex_escape(text):
    return str(text).replace("&", r"\&").replace("%", r"\%")


def verify_outputs(data, figures):
    records = load_records(data / "record_tags.csv")
    manifest = json.loads((data / "analysis_manifest.json").read_text())
    if manifest["input_sha256"] != sha256(data / "record_tags.csv") or manifest["script_sha256"] != sha256(Path(__file__)):
        raise ValueError("Input or script differs from the analysis manifest")
    for folder, key in [(figures, "files"), (data, "tables")]:
        for item in manifest[key]:
            if Path(item["path"]).name != item["path"] or sha256(folder / item["path"]) != item["sha256"]:
                raise ValueError(f"Output checksum mismatch: {item['path']}")
    print(f"Verified {len(records):,} frozen records, {len(manifest['files'])} figures, and {len(manifest['tables'])} table/snippet files.")


def generate_tex(result, destination):
    rows = [r for r in result["coverage"] if r["year"] == "All" and r["dimension"] in GROUPS]
    body = [r"\begin{tabular}{lrrr}", r"\toprule", r"Dimension & Tagged & Untagged & Coverage \\", r"\midrule"]
    for r in rows:
        title = GROUPS[r["dimension"]][1]
        body.append(f"{tex_escape(title)} & {r['tagged']:,} & {r['untagged']:,} & {r['coverage_pct']:.1f}\\% " + r"\\")
    body += [r"\bottomrule", r"\end{tabular}"]
    (destination / "coverage-table.tex").write_text("\n".join(body) + "\n")
    totals = [r for r in result["coverage"] if r["dimension"] == "Application Domain" and r["year"] != "All"]
    year_table = [r"\begin{tabular}{l*{10}{r}}", r"\toprule",
                  "Year & " + " & ".join(str(r["year"]) for r in totals) + r" \\",
                  r"Retained $N_y$ & " + " & ".join(f"{r['records']:,}" for r in totals) + r" \\",
                  r"\bottomrule", r"\end{tabular}"]
    (destination / "annual-denominators.tex").write_text("\n".join(year_table) + "\n")
    for group in ["AI models - DL", "Data type", "Concerns"]:
        lines = []
        for domain in result["categories"]["Application Domain"]:
            cells = sorted([r for r in result["cross"] if r["dimension"] == group and r["domain"] == domain],
                           key=lambda r: (-r["count"], r["category"]))
            n = cells[0]["domain_records"]
            descriptions = [f"{tex_escape(r['category'])} ({r['count']:,}/{n:,}; {r['within_domain_prevalence_pct']:.1f}\\%)" for r in cells[:3]]
            lines.append(r"\paragraph{" + tex_escape(domain) + ".}\\revnote{" +
                         "The three most frequent exported tags in this dimension are " + "; ".join(descriptions) + ".}")
        (destination / f"cross-{GROUPS[group][0]}-summary.tex").write_text("\n\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-workbook", type=Path)
    parser.add_argument("--data", type=Path, default=ROOT / "revision_data" / "reviewer2")
    parser.add_argument("--figures", type=Path, default=ROOT / "figures_revision2")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        if args.import_workbook:
            parser.error("--verify-only cannot import a workbook")
        verify_outputs(args.data, args.figures)
        return
    records = import_records(args.import_workbook, args.data) if args.import_workbook else load_records(args.data / "record_tags.csv")
    export_analysis(records, args.data, args.figures)


if __name__ == "__main__":
    main()
