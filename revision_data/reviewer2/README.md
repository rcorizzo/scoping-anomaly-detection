# Reviewer 2: Descriptive Figure Revision

## 1. Purpose and Input

This revision separates absolute publication counts, prevalence among retained records, and the composition of tag assignments. It does not rerun retrieval, change eligibility, infer new tags, or establish semantic classification accuracy.

The frozen `record_tags.csv` contains 11,079 retained rows from the public `data/2026-03-09/filtered_articles.xlsx` at source repository commit `6673b471ef6903b4921b7ef90e7c2c88fff87655`:

https://github.com/rcorizzo/scoping-anomaly-detection/tree/6673b471ef6903b4921b7ef90e7c2c88fff87655

Only hashed snapshot identifiers, publication years, and canonical category/source tags are retained. No names, abstracts, affiliations, contact fields, or links are copied into this table. Exported identifiers and links are unique within the source snapshot; no repeated nonmissing normalized DOI was found. There are 127 records without a DOI. Snapshot identifiers are not assumed stable across different runs.

`input_manifest.json` records the source workbook hash, frozen-table hash, taxonomy, and basic integrity checks. It is separate from the output hashes and software versions in `analysis_manifest.json`.

## 2. Regeneration

Use Python 3.12 and the pinned scientific packages. From the repository root:

```bash
python3 -m venv .venv-revision
.venv-revision/bin/python -m pip install -r scripts/requirements-revision.txt
.venv-revision/bin/python scripts/revision_analysis.py
.venv-revision/bin/python scripts/revision_analysis.py --verify-only
.venv-revision/bin/python -m unittest discover -s scripts -p 'test_revision_analysis.py' -v
```

The script reads the frozen CSV, validates its hash and identifier/year invariants, regenerates the tables and LaTeX summaries here, and writes vector PDFs plus PNG previews to `figures_revision2/`. It does not import or execute the original toolkit, crawl services, send mail, or alter the historical archives.

To reconstruct the frozen CSV from the publicly deposited workbook instead:

```bash
.venv-revision/bin/python scripts/revision_analysis.py \
  --import-workbook /path/to/data/2026-03-09/filtered_articles.xlsx
```

The workbook's directory must also contain `search_data_original.json` and `aggr_property_year.xlsx`. The reconstruction selects only native Boolean `is_article_relevant = True` rows, uses the semicolon-delimited canonical tags, and checks agreement with the archived annual property counts. Duplicate synonyms within a cell are reduced to a binary tag, not counted repeatedly.

## 3. Counting Rules

The counting unit is one retained export row aligned by its snapshot identifier. For category `a` and year `y`:

1. Absolute count: number of retained rows in year `y` with tag `a`.
2. Publication prevalence: that count divided by all retained rows in year `y`, multiplied by 100. Categories overlap, so prevalences need not sum to 100%.
3. Assignment composition: that count divided by all tag assignments in the same dimension and year, multiplied by 100. These shares sum to 100% when the assignment denominator is positive, but are not percentages of distinct publications.
4. Coverage: number of retained rows with at least one tag in a dimension, divided by all retained rows. Untagged rows remain in publication denominators and do not contribute assignments.
5. Cross-sections: a row contributes once to each domain/category co-occurrence. Cells show the count and its percentage of all retained rows with the domain tag, including those untagged in the compared dimension. Each cell is bounded by both category marginals.

Zero assignment denominators are exported as empty/not-applicable values, not as substantive zero-percent findings. Annual plots contain no such zero-denominator year in the current input.

The source-attribution figure uses the exported `all_sources` field, falling back to `source` when needed. Source labels can overlap and do not establish independent database coverage or actual source-query dates.

## 4. Outputs and Audit Boundaries

- `annual.csv`: all annual and overall counts, denominators, record prevalences, and assignment shares.
- `coverage.csv`: tagged/untagged row counts and union-based coverage, overall and by year.
- `cross.csv`: record-aligned domain/category counts, marginals, prevalences, and assignment shares.
- `annual-denominators.tex`, `coverage-table.tex`: generated manuscript tables.
- `cross-*-summary.tex`: generated top-three-tag summaries using the same cross-sectional calculations as the heatmaps.
- `analysis_manifest.json`: software versions, script hash, and figure/table hashes.

All archived annual tag counts are numerically reproducible from the retained export. This does not validate the tags' meaning. Coverage is computed directly from actual nonempty tag sets, not the `num_property_groups` summary field: that field can count empty group keys in the original toolkit.

The revised cross-sections are deliberately recomputed from the retained-record table rather than recycled from the separate archived heatmap postprocessor. Their common within-domain publication denominator replaces the earlier inconsistent percentage descriptions. Original plot assets remain archived, and the manuscript comments out the superseded plot blocks instead of deleting them.

The analysis is descriptive. It reports no hypothesis tests, confidence intervals, causal effects, manually assessed inter-rater agreement, or quality appraisal. Query provenance, cache history, missed studies, and semantic tagging errors require separate evidence. The figures and their numerical reproducibility must not be presented as validation of the historical search or the scientific quality of each retained study.
