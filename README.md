# Scoping Review of Applied Anomaly Detection

Code, data, and figures supporting *A Scoping Review of Applied Anomaly Detection: Trends, Insights, and Open Challenges*.

The approved results cover the full publication period **1 January 2016 through 31 December 2025**, including the complete 2025 calendar year. The quantitative map contains **11,079 retained bibliographic records** across application domains, data types, model families, learning settings, supervision terminology, and deployment-related topics.

## 1. Results

The results are available in **[data/2026-03-09/](data/2026-03-09/)**. The directory identifier records the processing date, 9 March 2026.

| Processing stage | Records |
| --- | ---: |
| Identified | 36,377 |
| Duplicates removed | 3,477 |
| After duplicate removal | 32,900 |
| Outside the publication period | 1,015 |
| Incomplete metadata | 15 |
| Assessed by the automated eligibility filter | 31,870 |
| Excluded by the eligibility filter | 20,791 |
| **Retained for descriptive mapping** | **11,079** |

The results directory includes record-level exports, search configurations, processing logs, 18 XLSX workbooks, 75 PDF outputs, and a BibTeX export. Dedicated contact lists are excluded and contact-email fields are removed from the public data.

### Main Files

| File | Contents |
| --- | --- |
| [`articles.xlsx`](data/2026-03-09/articles.xlsx) | Identified bibliographic records. |
| [`filtered_articles.xlsx`](data/2026-03-09/filtered_articles.xlsx) | Eligibility-stage records; select native Boolean `is_article_relevant = True` for the 11,079 retained records. |
| [`search_data_original.json`](data/2026-03-09/search_data_original.json) | Search vocabulary, category dictionaries, and processing configuration. |
| [`searched_data.json`](data/2026-03-09/searched_data.json) | Exported search configuration. |
| [`status.txt`](data/2026-03-09/status.txt) | Processing-stage log. |
| `aggr_*.xlsx` | Aggregate counts, annual summaries, property tables, and record-flow counters. |
| [`articles.bib`](data/2026-03-09/articles.bib) | Exported bibliographic records. |

## 2. Figures and Analysis Tables

The manuscript analysis is available in:

- **[figures_revision2/](figures_revision2/)**: 11 manuscript figures as vector PDFs and PNG previews: seven annual category plots, one source-attribution plot, and three domain cross-sections.
- **[revision_data/reviewer2/](revision_data/reviewer2/)**: the retained-record tag table, numerical CSV tables, generated LaTeX summaries, and analysis manifests.
- **[heatmaps_corrected/](heatmaps_corrected/)**: 45 additional pairwise co-occurrence heatmaps and their count workbook.
- **[figures_revision4/](figures_revision4/)**: the manuscript's automated record-flow diagram source.

Each annual category figure separates absolute record counts, prevalence among all retained records in that year, and the composition of category assignments. The three manuscript heatmaps show both record counts and percentages of all retained records with the corresponding domain tag.

**Manuscript reconciliation is completed for the retained total, publication window, and deposited analytical outputs.** The manuscript and response letter use 11,079 retained records and 2016--2025. The 11 active manuscript plot PDFs, frozen analysis input, and generated analysis tables match this repository by SHA-256. The verification inventory is available in [docs/manuscript-reconciliation.json](docs/manuscript-reconciliation.json).

## 3. Reproduce the Analysis Figures

Use Python 3.12 and the pinned scientific packages:

```bash
git clone https://github.com/rcorizzo/scoping-anomaly-detection.git
cd scoping-anomaly-detection
python3 -m venv .venv-revision
.venv-revision/bin/python -m pip install -r scripts/requirements-revision.txt
.venv-revision/bin/python scripts/revision_analysis.py
.venv-revision/bin/python scripts/revision_analysis.py --verify-only
.venv-revision/bin/python -m unittest discover -s scripts -p 'test_*.py' -v
```

The offline analysis reads the frozen, contact-free record/tag table and generates the figures, tables, and manuscript summaries. See the [analysis documentation](revision_data/reviewer2/README.md) for input reconstruction and counting rules.

## 4. Toolkit Source

The **[toolkit/](toolkit/)** directory contains the literature-analysis source: retrieval implementations, metadata filtering, duplicate handling, category extraction, aggregation, and visualization. Unrelated review datasets are excluded.

The supplied source revision is `65087b32ca5001c41726a67f00c3e5cee9ee47fe`. The [toolkit documentation](toolkit/README.md) describes its configuration, entry point, and output formats. Original dependency specifications and the Dockerfile are included.

## 5. Integrity and Data Handling

Verify the approved results:

```bash
python3 scripts/verify_snapshot.py --snapshot data/2026-03-09
python3 scripts/verify_snapshot.py --snapshot heatmaps_corrected
```

The verifier checks file inventories, sizes, SHA-256 checksums, workbook integrity, and contact-email removal. Each deposit includes a manifest and `SHA256SUMS`; the analytical outputs also have input and output manifests. [Results documentation](docs/snapshot-2026-03-09.md) describes the exported counts and manuscript correspondence.

## 6. Citation and Attribution

When referencing these artifacts, cite the associated manuscript, this repository, the results identifier `2026-03-09`, and the exact repository commit used. Commit permalinks identify a fixed version of the code, data, and figures.

For the retrieval methodology, see Zdravevski et al. (2019), [*Automation in Systematic, Scoping and Rapid Reviews by an NLP Toolkit: A Case Study in Enhanced Living Environments*](https://link.springer.com/chapter/10.1007/978-3-030-10752-9_1).

Bibliographic records retain publication and source attribution. Reuse is subject to the applicable source terms and original authors' rights.
