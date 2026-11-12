# Descriptive Analysis: Data and Figure Generation

## 1. Input

The analysis covers the full publication period **1 January 2016 through 31 December 2025** and uses **11,079 retained records** from [`data/2026-03-09/filtered_articles.xlsx`](../../data/2026-03-09/filtered_articles.xlsx).

The frozen `record_tags.csv` contains hashed record identifiers, publication years, and canonical category/source tags. `input_manifest.json` records the source workbook hash, frozen-table hash, taxonomy, and integrity checks. `analysis_manifest.json` records software versions, the generation-script hash, and figure/table hashes.

The source deposit is fixed at [commit `6673b47`](https://github.com/rcorizzo/scoping-anomaly-detection/tree/6673b471ef6903b4921b7ef90e7c2c88fff87655).

## 2. Regeneration

Use Python 3.12 and the pinned packages. From the repository root:

```bash
python3 -m venv .venv-revision
.venv-revision/bin/python -m pip install -r scripts/requirements-revision.txt
.venv-revision/bin/python scripts/revision_analysis.py
.venv-revision/bin/python scripts/revision_analysis.py --verify-only
.venv-revision/bin/python -m unittest discover -s scripts -p 'test_revision_analysis.py' -v
```

The offline script reads the frozen CSV, checks its hash and identifier/year invariants, generates tables and LaTeX summaries in this directory, and writes vector PDFs and PNG previews to `figures_revision2/`.

To reconstruct the frozen input from the deposited workbook:

```bash
.venv-revision/bin/python scripts/revision_analysis.py \
  --import-workbook data/2026-03-09/filtered_articles.xlsx
```

The workbook directory also contains `search_data_original.json` and `aggr_property_year.xlsx`. Reconstruction selects native Boolean `is_article_relevant = True` rows, reads semicolon-delimited canonical tags, and checks agreement with the exported annual property counts. Repeated synonyms within a category are represented by one binary tag.

## 3. Counting Rules

The counting unit is one retained record aligned by its snapshot identifier.

1. **Absolute count:** retained records in a year with a given category tag.
2. **Publication prevalence:** category count divided by all retained records in that year, multiplied by 100. Tags overlap, so prevalences need not sum to 100%.
3. **Assignment composition:** category count divided by all tag assignments in the same dimension and year, multiplied by 100. These shares sum to 100% when the assignment denominator is positive.
4. **Coverage:** retained records with at least one tag in a dimension, divided by all retained records. Untagged records remain in publication denominators and contribute no assignments.
5. **Cross-sections:** each record contributes once to a domain/category intersection. Cells report the count and its percentage of all retained records with the domain tag. Domain denominators include records untagged in the compared dimension; every cell is bounded by both marginals.

Source-attribution plots use `all_sources`, with `source` as a fallback. A record may have multiple source attributions. Zero assignment denominators are represented as not applicable.

## 4. Outputs

| File | Contents |
| --- | --- |
| `annual.csv` | Annual and overall counts, denominators, publication prevalences, and assignment shares. |
| `coverage.csv` | Tagged and untagged counts and coverage, overall and by year. |
| `cross.csv` | Domain/category intersection counts, marginals, prevalences, and assignment shares. |
| `annual-denominators.tex`, `coverage-table.tex` | Generated manuscript tables. |
| `cross-*-summary.tex` | Generated top-three-tag summaries using the heatmaps' calculations. |
| `input_manifest.json`, `analysis_manifest.json` | Input identity, software versions, and output checksums. |

The manuscript's 11 plot PDFs and generated numerical tables match the deposited analysis outputs. See the [manuscript reconciliation inventory](../../docs/manuscript-reconciliation.json).
