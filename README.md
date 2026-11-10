# Scoping Review of Anomaly Detection

Research artifacts supporting *A Scoping Review of Anomaly Detection: Trends, Insights, and Open Challenges*.

This repository contains the supplied literature-analysis toolkit and two separately versioned results snapshots. Contact lists are excluded, and contact-email fields are removed from public results. The supplied archives are not modified.

## 1. Current Results and Historical Snapshot

The newer results are deposited under **[data/2026-03-09/](data/2026-03-09/)**. This identifier follows the processing timestamps inside `status.txt`, not the July 2025 date in the archive name.

| Attribute | Newer results | Historical results |
| --- | --- | --- |
| Snapshot | [2026-03-09](data/2026-03-09/) | [2025-04-30](data/2025-04-30/) |
| Supplied archive | `results_Roberto_AnomalyDetection_20250717-5.zip` | `results_AnomalyDetection_20250430.zip` |
| Configured publication years | 2016 through 2025 | 2015 through 2025 |
| Logged processing date; timezone unspecified | 9 March 2026 | 30 April 2025 |
| Records identified through database searching | 36,377 | 19,231 |
| Records after duplicate removal | 32,900 | 18,423 |
| Records assessed for eligibility | 31,870 | 17,663 |
| Retained-record counter in the PRISMA export | **11,079** | 5,733 |
| Public archive-derived files | 99 | 61 |

**Manuscript reconciliation remains necessary.** The newer archive's 75 PDFs are byte-for-byte identical to all 75 assets in the manuscript's `figures_2026_3` directory at manuscript commit `a3b6539`. However, its retained-record counter is **11,079**, not the **19,884** stated in the manuscript text. The `filtered_articles.xlsx` export independently contains 11,079 rows flagged relevant and 20,791 flagged not relevant. This deposit documents that inconsistency; it does not resolve which corpus the manuscript should report.

The newer configuration includes the full publication-year window 2016--2025 and processing occurred after 2025. This supports a full-calendar-year eligibility window, but is not proof of exhaustive 2025 coverage or a fresh search on 9 March 2026: `force_crawl` is `false`, and cached retrieval may have been used. Source-specific query dates and execution provenance still require confirmation.

Detailed evidence and limitations are recorded in the [newer snapshot notes](docs/snapshot-2026-03-09.md), [historical snapshot notes](docs/snapshot-2025-04-30.md), and [manuscript figure comparison](docs/manuscript-figure-matches.json).

## 2. Repository Contents

```text
toolkit/                  Supplied source, without unrelated review data
  configuration/          Processing constants and configuration classes
  core/                   Search, filtering, similarity, and export logic
  crawlers/               Source-specific retrieval implementations
  help_tools/             Supporting utilities
  visual/                 Plotting, heatmaps, and PRISMA rendering
  main.py                 Original pipeline entry point
  README.md               Original toolkit documentation
  requirements*.txt       Original dependency specifications
  Dockerfile              Original container specification
  manifest.json           Archive inventory and exclusions
  SHA256SUMS
data/
  2026-03-09/              Newer results; recommended starting point
  2025-04-30/              Preserved historical results
docs/                     Provenance and interpretation notes
scripts/
  import_archives.py       Reproducible archive selection and sanitization
  verify_snapshot.py       Integrity and contact-removal checks
```

The newer results include 18 XLSX workbooks, 75 original PDFs, two JSON configurations, three processing/configuration TXT files, and a BibTeX export. Original archive-derived filenames are retained. The standalone `emails.txt` file is omitted.

### 2.1 Record-Level Exports

| File in `data/2026-03-09/` | Interpretation |
| --- | --- |
| [`articles.xlsx`](data/2026-03-09/articles.xlsx) | 36,377 exported records before the subsequent filtering stages. |
| [`filtered_articles.xlsx`](data/2026-03-09/filtered_articles.xlsx) | 31,870 eligibility-stage records, including both relevant and non-relevant rows; filter `is_article_relevant` for the pipeline-retained subset. |
| `articles_invalid.xlsx`, `articles_parsing_errors.xlsx` | Separate diagnostic exports; interpret with the archived code and logs. |
| [`articles.bib`](data/2026-03-09/articles.bib) | Pipeline-generated bibliography; this deposit does not certify bibliographic accuracy. |
| `filtered_graph_data.xlsx`, `filtered_graph_properties.xlsx` | Graph-analysis inputs and property summaries. |

Row counts exclude headers and are not independent verification of publication uniqueness, screening quality, or classification accuracy.

### 2.2 Configurations, Tables, and Figures

`search_data_original.json`, `searched_data.json`, and `search_data_simple.txt` preserve the supplied search vocabulary and processing options. `status.txt` and `status_long.txt` preserve stage and progress logs. Configuration files are not substitutes for the exact database-specific queries as executed.

`aggr_*.xlsx` contains annual counts, source summaries, property pivots, and PRISMA counters. The PDFs include category distributions, annual plots, pairwise heatmaps, source summaries, and graph visualizations. They are archived outputs, not recomputed figures. Pipeline labels such as "qualitative synthesis" and "meta-analysis" do not establish full-text synthesis or statistical pooling of study outcomes.

## 3. Toolkit Source and Execution Boundaries

The [toolkit source](toolkit/) comes from `article-analysis-65087b32ca5001c41726a67f00c3e5cee9ee47fe.zip`. The filename contains revision identifier `65087b32ca5001c41726a67f00c3e5cee9ee47fe`. This identifies the supplied source archive, **not a verified execution commit for either results snapshot**.

The deposit retains 51 source/documentation files unchanged. It excludes all 1,460 files under the source archive's `data/` directory, six ancillary reference/mockup files, a personal Git-setup script, a contact-list collection script, and the identical lowercase duplicate of `Dockerfile`. The [source manifest](toolkit/manifest.json) records each exclusion and the original/published file hashes. No unrelated review dataset or environment file is included.

Consult the [original toolkit README](toolkit/README.md) for configuration and implementation details. It is archival documentation, including its original terminology and claims. The original dependency files and Dockerfile are preserved; a working dependency environment and end-to-end reproduction have not been established by this deposit.

**Inspect before executing.** The original entry point can crawl external services, download models/data, send result notifications, and invoke a machine-specific results-commit script. The bundled `main_test.py` is not treated as an isolated offline test. Use a separate working copy, inspect configuration and paths, disable unwanted notifications/publication actions, and follow the source services' access terms. No crawler, mail sender, or publication script was executed to prepare this deposit.

## 4. Integrity and Privacy Verification

```bash
git clone https://github.com/rcorizzo/scoping-anomaly-detection.git
cd scoping-anomaly-detection
python3 scripts/verify_snapshot.py
```

The standard-library verifier checks both results snapshots and the toolkit inventory against their manifests and `SHA256SUMS`. For result files, it also checks workbook XML and text exports for remaining email addresses and populated dedicated `emails` cells. It verifies deposited artifact integrity and contact removal, not scientific validity, source-query reproducibility, or a functioning toolkit environment.

To verify one results snapshot:

```bash
python3 scripts/verify_snapshot.py --snapshot data/2026-03-09
```

To prepare a new local deposit from these original archives, use an empty destination:

```bash
python3 scripts/import_archives.py \
  --source /path/to/article-analysis-65087b32ca5001c41726a67f00c3e5cee9ee47fe.zip \
  --results /path/to/results_Roberto_AnomalyDetection_20250717-5.zip \
  --destination /path/to/empty-deposit
```

The standalone contact list is excluded. Dedicated `emails` workbook cells are blanked, and other email-address occurrences in workbook XML, configurations, or bibliographic text are replaced with `[email redacted]`. The manifests identify transformed files; scientific values are otherwise preserved. Original archives and raw contact-containing extracts are not committed.

## 5. Use in the Rebuttal

The repository now supplies source code as well as archived configurations, processing logs, record-level exports, aggregate tables, and figure assets. For the newer results, internal relevance counts agree with the PRISMA export and the PDF assets match the current manuscript figure directory exactly.

Remaining issues include:

1. Reconciling the manuscript's 19,884 retained records with this snapshot's 11,079.
2. Confirming the actual source-query dates, cache history, and source-code version used for the run.
3. Documenting any human screening, full-text assessment, and classification validation.
4. Checking publication uniqueness, overlapping tags, heatmap denominators, and numerical claims.
5. Establishing a tested environment and regenerating outputs before claiming computational reproduction.

Suggested factual wording:

> We have deposited the supplied analysis-toolkit source, excluding unrelated review datasets, together with the newer results snapshot whose processing logs are dated 9 March 2026. The repository includes search configurations, processing logs, bibliographic exports, aggregate workbooks, and original figure assets, with contact-email removal and file checksums documented. The snapshot contains 11,079 pipeline-retained records. Reconciliation of this count with the manuscript text, confirmation of query/execution provenance, and classification validation remain separate tasks.

## 6. Version Identification and Attribution

For a final response letter, cite this repository, the results snapshot identifier `2026-03-09`, and the exact Git commit containing the deposit. Use a commit permalink so that the referenced artifacts remain fixed. Source-archive hashes and per-file transformations are recorded in each manifest.

The historical April snapshot remains available and unchanged. Its original source hash is documented in its manifest and snapshot notes.

Bibliographic records retain source and publication identifiers. Reuse remains subject to applicable source terms and the original authors' rights. No new license is assigned to third-party records, reference material, or the supplied toolkit by this deposit.
