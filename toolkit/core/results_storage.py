from __future__ import annotations

from collections import Counter
from typing import Dict

import pandas as pd
from pandas import DataFrame

from configuration.config import Config
from core.search_config import SearchConfig
from help_tools import helpers as h, hio


def save_results_aggr_source(search: SearchConfig):
    result_aggr_source = [['source'] + Config.PRISMA_search_stats_header]
    for source, d in search.result_counts.items():
        result_aggr_source.append([source] + [d.get(stat, 0) for stat in Config.PRISMA_search_stats_header])
    h.write_csv_and_excel_file(result_aggr_source, search.file_results_aggr_source, separator='\t')


def save_results_aggr_year(search, per_year):
    result_aggr_year = [['year', 'analyzed_articles', 'relevant_articles']]
    result_aggr_year += sorted([tuple([year] + v) for year, v in per_year.items()])
    h.write_csv_and_excel_file(result_aggr_year, search.file_results_aggr_year, separator='\t')


def save_results_aggr_source_year(search: SearchConfig, source_year):
    result_aggr_source_year = [['source', 'year', 'analyzed_articles', 'relevant_articles']]
    result_aggr_source_year += sorted([tuple(list(k) + v) for k, v in source_year.items()])
    h.write_csv_and_excel_file(result_aggr_source_year, search.file_results_aggr_source_year, separator='\t')


def save_result_aggr_source_year_pivot(search: SearchConfig, sources: list, years: list, source_year: dict):
    __save_results_aggr_source_year_pivot(search.file_results_aggr_source_year_pivot_analyzed, sources, years,
                                          source_year, 0)
    __save_results_aggr_source_year_pivot(search.file_results_aggr_source_year_pivot_relevant, sources, years,
                                          source_year, 1)


def __save_results_aggr_source_year_pivot(filename: str, years: list, sources: list, source_year: dict, index: int):
    result_aggr_source_year_pivot_analyzed = [['source'] + years]
    for source in sources:
        result_aggr_source_year_pivot_analyzed.append(
            [source] + [source_year.get((source, year), [0, 0])[index] for year in years])

    h.write_csv_and_excel_file(result_aggr_source_year_pivot_analyzed, filename, separator='\t')


def save_results_aggr_keyword_year_pivot_relevant(search: SearchConfig, keywords: list, years: list,
                                                  keyword_year: Dict):
    result_aggr_keyword_year_pivot_relevant = [['keyword'] + sorted(years)]
    for keyword in keywords:
        result_aggr_keyword_year_pivot_relevant.append(
            [keyword] + [keyword_year.get((keyword, year), [0, 0])[1] for year in sorted(years)])

    h.write_csv_and_excel_file(result_aggr_keyword_year_pivot_relevant,
                               search.file_results_aggr_keyword_year_pivot_relevant,
                               separator='\t')


def save_results_aggr_keyword_source_pivot_relevant(search: SearchConfig, sources: list, keywords: list,
                                                    keyword_source: dict):
    result_aggr_keyword_source_pivot_relevant = [['keyword'] + sources]
    for keyword in keywords:
        result_aggr_keyword_source_pivot_relevant.append(
            [keyword] + [keyword_source.get((keyword, source), [0, 0])[1] for source in sources])

    h.write_csv_and_excel_file(result_aggr_keyword_source_pivot_relevant,
                               search.file_results_aggr_keyword_source_pivot_relevant,
                               separator='\t')


def save_results_property_groups(search: SearchConfig, years: list,
                                 aggr_prop_group_year: dict, property_group_property_year_counter: Counter,
                                 selected: int):
    prop_groups = sorted(search.property_groups.keys())
    result_aggr_prop_group_year = [['property_group', 'year', 'article_count']]
    result_aggr_prop_group_year += [(pg, y, aggr_prop_group_year.get((pg, y), 0)) for pg in prop_groups for y in
                                    years]

    result_aggr_prop_group_year_pivot = [['property_group'] + years]
    for property_group in prop_groups:
        l = [property_group] + [aggr_prop_group_year.get((property_group, y), '0') for y in years]
        result_aggr_prop_group_year_pivot.append(l)

    h.write_csv_and_excel_file(result_aggr_prop_group_year_pivot, search.file_results_aggr_property_group_year_pivot,
                               separator='\t')

    data = [[property_group, property, year, cnt] for (property_group, property, year), cnt in
            property_group_property_year_counter.items()]
    data_property_group_property_cnt = Counter()
    data_property_group_property_l = list()
    for property_group, property, year, cnt in data:
        data_property_group_property_cnt[(property_group, property)] += cnt
    for (property_group, property), cnt in data_property_group_property_cnt.items():
        data_property_group_property_l.append([property_group, property, cnt, cnt / selected])

    # TODO: save data_property_group_property_l into a new file
    df_percentage = pd.DataFrame(data_property_group_property_l,
                                 columns=['property_group', 'property', 'cnt', 'percentage'])
    hio.df_to_csv(df_percentage, search.file_results_property_group_percentage)
    df = pd.DataFrame(data, columns=['property_group', 'property', 'year', 'cnt'])
    hio.df_to_csv(df, search.file_results_aggr_property_year, write_to_excel_too=True)
    df_pivot = pd.pivot_table(df, values='cnt', index=['property_group', 'property'], columns='year',
                              aggfunc='sum', fill_value=0)
    df_pivot.reset_index(inplace=True)
    hio.df_to_csv(df_pivot, search.file_results_aggr_property_year_pivot, write_to_excel_too=True, index=True)


def save_results_aggr_num_countries_affiliations_authors(search, country_affil_authors):
    lcountry_affil_authors = [['num_countries', 'num_affiliations', 'num_authors', 'relevant_articles']] + sorted(
        [list(k) + [v] for k, v in country_affil_authors.items()])

    h.write_csv_and_excel_file(lcountry_affil_authors, search.file_results_aggr_num_countries_affiliations_authors,
                               separator='\t')


def save_filtered_articles(search: SearchConfig, invalid_rows: list, relevant_articles: list, is_rerun: bool):
    sort_columns = ['num_property_groups', 'num_properties', 'year', 'source', 'citations', 'title']
    ascending_flag = [False, False, False, True, False, True]
    df_columns = search.hd_output_property_groups
    if search.calculate_similarities:
        df_columns = df_columns + ['BGELarge_Similarity', 'UAELarge_Similarity']

    df_invalid_rows = DataFrame(invalid_rows, columns=df_columns)
    df_invalid_rows.to_csv(search.file_results_articles_invalid, sep='\t', index=False)
    h.csv_to_excel(search.file_results_articles_invalid)

    df_output_property_groups_fil = DataFrame(relevant_articles, columns=df_columns)
    df_output_property_groups_fil.sort_values(sort_columns, ascending=ascending_flag, inplace=True)
    if search.calculate_similarities:
        df_output_property_groups_fil["BGELarge_Rank"] = df_output_property_groups_fil["BGELarge_Similarity"].rank(ascending=False, method="dense").astype(int)
        df_output_property_groups_fil["UAELarge_Rank"] = df_output_property_groups_fil["UAELarge_Similarity"].rank(ascending=False, method="dense").astype(int)
    file_filtered_articles = search.file_results_articles_filtered
    if is_rerun:
        file_filtered_articles = h.remove_extension(file_filtered_articles) + '_manually_selected.csv'
    df_output_property_groups_fil.to_csv(file_filtered_articles, sep='\t', index=False)
    h.csv_to_excel(file_filtered_articles)

    with open(search.filename_input_simple, mode='w', encoding='utf-8') as f:
        f.write(search.search_input_text(True))
