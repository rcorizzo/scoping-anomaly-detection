import os
import shutil
from collections import Counter
from itertools import combinations
from typing import Dict, Tuple, Set

import pandas as pd

from configuration.config import Config
from core.bibtex_helpers import create_bibtex_entries, generate_bibtex_file
from core.results_storage import save_results_aggr_source, save_results_aggr_source_year, \
    save_results_aggr_keyword_year_pivot_relevant, \
    save_results_aggr_keyword_source_pivot_relevant, save_result_aggr_source_year_pivot, \
    save_results_property_groups, save_results_aggr_year, \
    save_results_aggr_num_countries_affiliations_authors, save_filtered_articles
from core.search_config import SearchConfig
from help_tools import helpers as h
from help_tools import hio
from help_tools.helpers import create_folder, remove_extension, write_csv_and_excel_file
from help_tools.helpers import is_email_valid
from help_tools.tools import tools
from visual.bar_plots import plot_property_group_percentage, plot_year_property, plot_year_property_group
from visual.chart_helpers import prepare_property_group_properties_counts_df
from visual.heatmap import heatmap_graph_data
from visual.output_results import plot_all
from visual.prisma import generate_prisma_output
from core.text_similarities import embed_articles

def _merge_crawled_articles(search: SearchConfig):
    h.log_line('Merging crawling results...')
    search.set_status('Merge Scraped Articles', 'Starting')
    data = []
    # for source, sql_filename in search.result_files:
    for filename in search.result_files:
        if os.path.isfile(filename) and os.stat(filename).st_size > 0:
            cdata, hd = h.read_csv_file(filename, 'str', True, separator='\t', has_header=True)
            data.extend(cdata)

    data = [Config.keywords_result_header] + data
    h.write_csv_and_excel_file(data, search.file_articles_all, separator='\t')
    df = pd.read_csv(search.file_articles_all, sep='\t', header=0)
    h.log_line('Finished merging articles')
    search.set_status('Merge Scraped Articles')
    search.to_pickle()
    return df


def stem_articles(search: SearchConfig, df: pd.DataFrame = None):
    h.log_line('Tokenizing articles...')
    search.set_status('Tokenizing articles', 'Starting')
    df.fillna('', inplace=True)
    print(df)
    if not df.empty:
        df['abstract_stemmed'] = df.apply(
            lambda row: tools.stem_text(row["abstract"] + ' ' + row["title"], search.apply_stemming, search.remove_stopwords), axis=1)
    df.to_csv(search.file_articles_stemmed, sep='\t', index=False)
    search.to_pickle()
    search.set_status('Tokenizing articles')
    h.log_line('Finished tokenizing articles.')


def check_if_article_is_relevant(row: pd.Series, search: SearchConfig,
                                 aggr_prop_year: Dict[Tuple[str, int], int],
                                 aggr_prop_group_year: Dict[Tuple[str, int], int],
                                 properties_counter: Counter,
                                 property_pairs: Counter,
                                 property_group_property_year_counter: Counter,
                                 matched_properties_flat: Set[str],
                                 matched_property_groups: Dict,
                                 df: pd.DataFrame = None):
    """

    :param row:
    :param search:
    :param aggr_prop_year:
    :param aggr_prop_group_year:
    :param properties_counter:
    :param property_pairs:
    :param property_group_property_year_counter:
    :param matched_properties_flat:
    :param matched_property_groups:
    :param df: File with manually filtered data
    :return:
    """
    matched_property_group_property = set()
    abstract_stemmed_tup = tools.text_to_tuple(row.abstract_stemmed)
    properties_mandatory_satisfied = True
    for properties_mandatory_OR_group in search.properties_mandatory_stemmed:
        mandatory_property_current = False
        for mandatory_property_OR in properties_mandatory_OR_group:
            if tools.is_subsequence(mandatory_property_OR, abstract_stemmed_tup):
                mandatory_property_current = True
                break
        properties_mandatory_satisfied = properties_mandatory_satisfied and mandatory_property_current
        if not properties_mandatory_satisfied:
            break
    if properties_mandatory_satisfied:
        for property_excluded in search.properties_excluded_stemmed:
            if tools.is_subsequence(property_excluded, abstract_stemmed_tup):
                properties_mandatory_satisfied = False
                break
    found_prop_ext = []
    major_property_to_property_group_map = {}
    for group in search.properties:
        property_group = group["property_group"]
        synonyms_list = group["synonyms"]

        major_property_to_property_group_map[property_group] = [synonym[0] for synonym in synonyms_list]
    for stemmed_property_tup, prop_groups in search.property_stem_lookup_tuple.items():
        if tools.is_subsequence(stemmed_property_tup, abstract_stemmed_tup):
            full_property_str = search.stem_source_lookup_tuple[stemmed_property_tup]
            for k, major_property in enumerate(search.property_synonym_lookup[full_property_str]):
                matched_properties_flat.add(major_property)
                for prop_group in search.property_lookup[major_property]:
                    matched_property_groups.setdefault(prop_group, set())
                    if major_property in major_property_to_property_group_map[prop_group]:
                        matched_property_groups[prop_group].add(major_property)

    is_article_relevant_auto = properties_mandatory_satisfied and len(matched_properties_flat) >= search.relevant
    is_article_relevant = is_article_relevant_auto
    is_article_relevant_manual = False
    if df is not None and 'is_article_relevant' in df.columns:
        try:
            is_article_relevant_manual = df[df.title_simplified == row.title_simplified]['is_article_relevant'].values[
                0]
        except Exception as e:
            h.log_line(f"Link doesn't exist. Skipping {row.link}", e)
            is_article_relevant_manual = False
        is_article_relevant = is_article_relevant_manual

    if is_article_relevant:
        for prop_group, major_properties in matched_property_groups.items():
            aggr_prop_group_year.setdefault((prop_group, row.year), 0)
            aggr_prop_group_year[(prop_group, row.year)] += 1
            for major_property in major_properties:
                properties_counter[(prop_group, major_property)] += 1
                property_group_property_year_counter[(prop_group, major_property, row.year)] += 1
                matched_property_group_property.add((prop_group, major_property))

        for major_property in matched_properties_flat:
            aggr_prop_year.setdefault((major_property, row.year), 0)
            aggr_prop_year[(major_property, row.year)] += 1

        for combination in combinations(matched_property_group_property, 2):
            key = tuple(sorted(combination))
            property_pairs[key] += 1
    return is_article_relevant_auto, is_article_relevant_manual, is_article_relevant


def update_relevant_selected_count_per_source(all_sources_with_this_article: set, result_counts, is_auto_relevant,
                                              is_manually_relevant):
    for each_source_with_this_article in all_sources_with_this_article:
        if is_auto_relevant:
            result_counts[each_source_with_this_article][Config.PRISMA_relevant] += 1
        if is_manually_relevant:
            result_counts[each_source_with_this_article][Config.PRISMA_selected] += 1


def update_counts_per_article(row: pd.Series, per_year: Dict, source_year: Dict, per_keyword: Dict,
                              keyword_year: Dict, keyword_source: Dict, search: SearchConfig, index: int,
                              all_keywords_with_this_article: Set = None, all_sources_with_this_article: Set = None):
    """
    Updates the counts in each relevant dict for an article (row) that is being processed, after deduping

    :param row: the current row in the df
    :param per_year:
    :param source_year:
    :param per_keyword:
    :param keyword_year:
    :param keyword_source:
    :param search:
    :param index: 0 means considered, 1 means relevant
    :param all_keywords_with_this_article:
    :param all_sources_with_this_article:
    :return:
    """

    per_year[row.year][index] += 1

    # set the "considered" counts for all sources with this article
    for each_source_with_this_article in all_sources_with_this_article:
        source_year.setdefault((each_source_with_this_article, row.year), [0, 0])
        source_year[(each_source_with_this_article, row.year)][index] += 1
        if index == 0:
            search.result_counts.setdefault(each_source_with_this_article, {})
            search.result_counts[each_source_with_this_article].setdefault(Config.PRISMA_remaining, 0)
            search.result_counts[each_source_with_this_article].setdefault(Config.PRISMA_relevant, 0)
            search.result_counts[each_source_with_this_article].setdefault(Config.PRISMA_selected, 0)
            search.result_counts[each_source_with_this_article][Config.PRISMA_remaining] += 1

    # set the "considered" counts for all keywords with this article
    for each_keyword_with_this_article in all_keywords_with_this_article:
        keyword_year.setdefault((each_keyword_with_this_article, row.year), [0, 0])
        keyword_year[(each_keyword_with_this_article, row.year)][index] += 1
        per_keyword.setdefault(each_keyword_with_this_article, [0, 0])
        per_keyword[each_keyword_with_this_article][index] += 1

    # set the "considered" counts for all (keyword, source) pairs with this article
    for each_source_with_this_article in all_sources_with_this_article:
        for each_keyword_with_this_article in all_keywords_with_this_article:
            keyword_source.setdefault((each_keyword_with_this_article, each_source_with_this_article), [0, 0])
            keyword_source[(each_keyword_with_this_article, each_source_with_this_article)][index] += 1


def retrieve_query(query_raw: Dict):
    """
    Retrieve query in text format from JSON format
    """

    query = []
    search_properties = query_raw["properties"]
    for property_group_row in search_properties:
        property_group_name = property_group_row['property_group']

        properties = property_group_row['synonyms']
        properties_result = []
        for property_row in properties:
            property_row_join = ', '.join(property_row)
            properties_result.append(property_row_join)

        properties_result = '; '.join(properties_result)
        property_group_result = f'{property_group_name}: {properties_result}'
        query.append(property_group_result)

    query = '.\n'.join(query)

    return query


def process_articles(search: SearchConfig, df: pd.DataFrame = None, file_manually_filtered_articles: str = None):
    search.set_status('Process articles', 'Starting')
    if df is None:
        df = _merge_crawled_articles(search)
    tools.df_as_str(df)
    bibtex_ids, bibtex_doi_ids = create_bibtex_entries(search, df)
    stem_articles(search, df)

    search.write_results(search.parsing_errors_articles, search.file_articles_file_articles_parsing_errors)

    relevant_articles = []
    aggr_prop_group_year = dict()
    aggr_prop_year = dict()
    dois = set()
    titles = set()
    links = set()
    years = set()
    retained_dois = set()
    source_year = dict()
    per_year = dict()
    sources = set()
    per_keyword = dict()
    keyword_source = dict()
    keyword_year = dict()
    keywords = set()
    properties_counter = Counter()
    property_group_property_year_counter = Counter()
    property_pairs = Counter()
    country_affil_authors = dict()
    graph_data = [['doi', 'affiliations', 'countries', 'properties']]
    duplicates_removed = 0
    skipped_other = 0
    invalid_years = 0
    considered = len(df)
    relevant = 0
    selected = 0
    identified_other = 0
    is_rerun = False
    df_manually_filtered = None
    try:
        if file_manually_filtered_articles:
            df_manually_filtered = hio.pd_read_csv_or_excel(file_manually_filtered_articles)
            expected = set(Config.keywords_result_header)
            got = set(df_manually_filtered.columns)
            df_manually_filtered['title_simplified'] = df_manually_filtered.apply(
                lambda row: h.remove_nonalpha(row.title), axis=1)
            missing_columns = expected.difference(got)
            h.log_line(expected == got)
            if len(missing_columns) > 0:
                h.log_line(
                    f"Missing columns:{sorted(missing_columns)} in provided file: {file_manually_filtered_articles}"
                    f".\n\t Expected columns: {sorted(expected)}\nProvided columns:{sorted(got)}\nTERMINATING!")
                exit(1)

            # Identify what values are in TableB and not in TableA
            key_diff = set(df_manually_filtered.link).difference(df.link)
            manually_added_articles_mask = df_manually_filtered.link.isin(key_diff)

            needed_columns = df.columns[:-2]
            # all columns as the source, except 'abstract_stemmed', 'bibtex_id'
            df_manually_added_articles = df_manually_filtered[manually_added_articles_mask][needed_columns]
            df_manually_added_articles['bibtex_id'] = ""
            tools.df_as_str(df_manually_added_articles)
            identified_other = len(df_manually_added_articles)
            if identified_other > 0:
                stem_articles(search, df_manually_added_articles)
                # Slice TableB accordingly and append to TableA
                df = pd.concat([df, df_manually_added_articles])
            is_rerun = True
    except Exception as e:
        h.log_line("Provided file is not in the expected format.", e)
        df_manually_filtered = None
        is_rerun = False
        identified_other = 0
        exit(1)
    search.set_result_counts(set(df.source.values))
    invalid_rows = []
    df['valid_doi'] = df.apply(lambda row: tools.extract_doi(row.doi), axis=1)
    df['title_simplified'] = df.apply(lambda row: h.remove_nonalpha(row.title), axis=1)
    df['emails'] = df.apply(lambda row: row.emails.strip('.').strip(';'), axis=1)
    df_emails_rows = df[df['emails'] != '']
    emails_rows = df_emails_rows['emails'].values.tolist()
    all_emails = []
    for x in emails_rows:
        all_emails.extend([y for y in str(x).split(';') if is_email_valid(y)])
    all_emails = sorted(set(all_emails))
    all_emails_str = '\n'.join(all_emails)
    with open(search.file_emails, mode='w') as f:
        f.write(all_emails_str)

    for i, row in df.iterrows():
        search.result_counts[row.source][Config.PRISMA_considered] += 1
        try:
            row.year = int(row.year)
            if h.is_emptyz(row.year):
                h.log_line(f'Skipping. Year value not valid: {row.year}')
                invalid_years += 1
                search.result_counts[row.source][Config.PRISMA_invalid_years] += 1
                invalid_rows.append(row)
                continue

            if not search.start_year <= float(row.year) <= search.end_year:
                h.log_line(f'Skipping. Year Issue: {search.start_year}<={float(row.year)}<={search.end_year}')
                invalid_years += 1
                search.result_counts[row.source][Config.PRISMA_invalid_years] += 1
                continue

            if float(row.num_diff_affiliations) > Config.max_article_affiliations:
                h.log_line('Skipping. Article has too many affiliations:', row.num_diff_affiliations)
                skipped_other += 1
                search.result_counts[row.source][Config.PRISMA_incomplete_data] += 1
                continue
            if float(row.num_authors) > Config.max_article_authors:
                h.log_line('Skipping. Article has too many authors:', row.num_authors)
                search.result_counts[row.source][Config.PRISMA_incomplete_data] += 1
                skipped_other += 1
                continue
        except Exception as e:
            h.log_line('Skipping. Article has some invalid values in the parsed columns:', row)
            invalid_rows.append(row)
            search.result_counts[row.source][Config.PRISMA_parsing_errors] += 1
            continue

        # set defaults
        keywords.add(row.keyword)
        matched_property_groups = dict()
        matched_properties_flat = set()
        years.add(row.year)
        sources.add(row.source)
        keyword_year.setdefault((row.keyword, row.year), [0, 0])
        per_keyword.setdefault(row.keyword, [0, 0])
        source_year.setdefault((row.source, row.year), [0, 0])
        per_year.setdefault(row.year, [0, 0])

        search.result_counts.setdefault(row.source, {})
        search.result_counts[row.source].setdefault(Config.PRISMA_relevant, 0)
        country_affil_authors.setdefault((row.num_diff_countries, row.num_diff_affiliations, row.num_authors),
                                         0)
        # TODO: THIS IS CORRECT, BUT BECAUSE SPRINGER PARSER WORKS INCORRECTLY FOR DOIS, IT DOESN'T WORK
        # if row.valid_doi:
        #     all_sources_with_this_article = set(df[df.valid_doi == row.valid_doi]["source"])
        #     all_keywords_with_this_article = set(df[df.valid_doi == row.valid_doi]["keyword"])
        # else:
        #     all_sources_with_this_article = set(df[df.link == row.link]["source"])
        #     all_keywords_with_this_article = set(df[df.link == row.link]["keyword"])
        all_sources_with_this_article = set(df[df.title_simplified == row.title_simplified]["source"])
        all_keywords_with_this_article = set(df[df.title_simplified == row.title_simplified]["keyword"])
        all_keywords_with_this_article_str = ';'.join(sorted(all_keywords_with_this_article))
        all_sources_with_this_article_str = ';'.join(sorted(all_sources_with_this_article))
        for keyword in all_keywords_with_this_article:
            for source in all_sources_with_this_article:
                keyword_source.setdefault((keyword, source), [0, 0])

        # if row.link in links or (row.valid_doi and row.valid_doi in dois):
        if row.link in links:
            h.log_line(f'Skipping. Article with same link:{row.link} exists:')
            duplicates_removed += 1
            search.result_counts[row.source][Config.PRISMA_duplicates] += 1
            continue
        elif row.title_simplified in titles:
            h.log_line(
                f'Skipping. Article with same Title exists doi:{row.valid_doi}, link:{row.link} '
                f'title:{row.title} exists:')
            duplicates_removed += 1
            search.result_counts[row.source][Config.PRISMA_duplicates] += 1
            continue
        elif row.doi and row.doi in dois:
            h.log_line(
                f'Skipping. Article with same doi exists:{row.valid_doi}, link:{row.link} title:{row.title} exists:')
            duplicates_removed += 1
            search.result_counts[row.source][Config.PRISMA_duplicates] += 1
            continue
        else:
            if row.valid_doi:
                dois.add(row.valid_doi)
            links.add(row.link)
            titles.add(row.title_simplified)

        # FROM NOW ON, NO DUPLICATES
        update_counts_per_article(row, per_year, source_year, per_keyword, keyword_year, keyword_source, search, 0,
                                  all_keywords_with_this_article, all_sources_with_this_article)

        # CHECK IF ARTICLE IS RELEVANT OR NOT
        is_article_relevant_auto, is_article_relevant_manual, is_article_relevant = \
            check_if_article_is_relevant(row,
                                         search,
                                         aggr_prop_year,
                                         aggr_prop_group_year,
                                         properties_counter,
                                         property_pairs,
                                         property_group_property_year_counter,
                                         matched_properties_flat,
                                         matched_property_groups,
                                         df_manually_filtered)

        update_relevant_selected_count_per_source(all_sources_with_this_article, search.result_counts,
                                                  is_article_relevant_auto,
                                                  is_article_relevant_manual)
        if is_article_relevant_auto:
            relevant += 1

        if is_article_relevant:
            selected += 1

        if is_article_relevant:
            if row.valid_doi:
                retained_dois.add(row.valid_doi)
            update_counts_per_article(row, per_year, source_year, per_keyword, keyword_year, keyword_source,
                                      search, 1, all_keywords_with_this_article, all_sources_with_this_article)
            graph_data.append(
                [row.valid_doi, row.affiliations, row.countries, ';'.join(sorted(matched_properties_flat))])
        row.doi = row.valid_doi
        record_keys = Config.keywords_result_header_extended[:-2] + [Config.keywords_result_header_extended[-1]]
        record_simple = row[record_keys]
        record_simple = [str(r)[:Config.abstract_export_max_length] for r in record_simple]
        included, comment = None, None

        record_summary = [str(len(matched_property_groups)), str(len(matched_properties_flat)),
                              all_keywords_with_this_article_str, all_sources_with_this_article_str, is_article_relevant, included, comment]

        found_prop_ext = []
        for prop_group in search.property_groups_sorted:
            p = matched_property_groups.get(prop_group, set())
            pm = ';'.join(sorted(p))
            found_prop_ext.append(pm)

        row_relevant_article = list(record_simple) + record_summary + found_prop_ext

        relevant_articles.append(row_relevant_article)
        if i % 100 == 0:
            search.set_status('Process articles', f'Line {i} of {len(df)}')
            h.log_line('Process articles. Line', i, 'of', len(df), 'in file:', search.file_articles_stemmed)

    years = sorted(years)
    sources = sorted(sources)
    keywords = sorted(keywords)

    # save outputs
    prepare_property_group_properties_counts_df(properties_counter, property_pairs,
                                                search.file_filtered_graph_properties)
    properties_query = retrieve_query(search.search_data)

    search.to_pickle()
    generate_bibtex_file(search, bibtex_ids, bibtex_doi_ids, retained_dois)

    h.write_csv_and_excel_file(graph_data, search.file_results_graph_data, separator='\t')
    save_results_aggr_source(search)
    save_results_aggr_source_year(search, source_year)
    save_results_aggr_year(search, per_year)
    save_results_aggr_keyword_year_pivot_relevant(search, keywords, years, keyword_year)
    save_results_aggr_keyword_source_pivot_relevant(search, sources, keywords, keyword_source)
    save_result_aggr_source_year_pivot(search, years, sources, source_year)

    save_results_property_groups(search, years, aggr_prop_group_year, property_group_property_year_counter, selected)
    # TODO: this is not properly working
    save_results_aggr_num_countries_affiliations_authors(search, country_affil_authors)

    generate_prisma_output(search.file_results_aggr_source, search.file_results_aggr_prisma, identified_other,
                           skipped_other, invalid_years, duplicates_removed, considered, relevant, selected)
    relevant_articles = embed_articles(relevant_articles, properties_query)
    save_filtered_articles(search, invalid_rows, relevant_articles, is_rerun)

    # COPY used files
    shutil.copyfile(search.filename_json, search.file_searched_keywords_final)

    plot_all(search)
    search.set_status('Process articles')


def process_manually_analyzed_files(filename_json, filename_selected, property_groups_selected, heatmap_groups=None):
    """
    Creates all percentage, trend and heatmap charts based on a manually created excel file.

    :param filename_json: The original json file used for the first run
    :param filename_selected: A file where each row is a new article, it has a "Year" column, and then it has other columns corresponding to property groups
    :param property_groups_selected: lists of strings specifying the property group combinations (columns in the excel file)
    :param heatmap_groups: List of lists of strings specifying the property group combinations
    :return:
    """
    search = SearchConfig.load_object(filename_json)
    manual_articles_df = hio.pd_read_csv_or_excel(filename_selected)
    group_prop_year_counter = Counter()
    properties_counter = Counter()
    property_pairs = Counter()
    aggr_prop_group_year = Counter()
    years = set()
    import re
    resplit = re.compile(r'[,;]')
    for index, row in manual_articles_df.iterrows():
        matched_property_group_property = set()
        for prop_group in property_groups_selected:
            if type(row[prop_group]) is str:
                properties_list = resplit.split(row[prop_group])
                year = row['Year']
                years.add(year)
                aggr_prop_group_year[(prop_group, year)] += 1
                for property in properties_list:
                    property = property.strip()
                    properties_counter[(prop_group, property)] += 1
                    group_prop_year_counter[(prop_group, property, year)] += 1

                    matched_property_group_property.add((prop_group, property))

        for combination in combinations(matched_property_group_property, 2):
            key = tuple(sorted(combination))
            property_pairs[key] += 1
        continue
    create_folder(search.folder_results)

    # property group charts
    fn_property_group_year_pivot = remove_extension(search.file_results_aggr_property_group_year_pivot) + '_manual.csv'
    years = sorted(years)
    result_aggr_prop_group_year = [['property_group', 'year', 'article_count']]
    result_aggr_prop_group_year += [(pg, y, aggr_prop_group_year.get((pg, y), 0)) for pg in property_groups_selected for
                                    y in years]

    result_aggr_prop_group_year_pivot = [['property_group'] + years]
    for property_group in property_groups_selected:
        l = [property_group] + [aggr_prop_group_year.get((property_group, y), '0') for y in years]
        result_aggr_prop_group_year_pivot.append(l)

    write_csv_and_excel_file(result_aggr_prop_group_year_pivot, fn_property_group_year_pivot,
                             separator='\t')
    plot_year_property_group(fn_property_group_year_pivot, **search.plotting)

    # property charts
    data_manual = [[group, property, year, cnt] for (group, property, year), cnt in group_prop_year_counter.items()]
    df = pd.DataFrame(data_manual, columns=['property_group', 'property', 'year', 'cnt'])

    fn_property_year = remove_extension(search.file_results_aggr_property_year) + '_manual.csv'
    fn_property_year_pivot = remove_extension(search.file_results_aggr_property_year_pivot) + '_manual.csv'
    hio.df_to_csv(df, fn_property_year, write_to_excel_too=True)
    fn_prop = remove_extension(search.file_filtered_graph_properties) + '_manual.csv'

    df_pivot = pd.pivot_table(df, values='cnt', index=['property_group', 'property'], columns='year',
                              aggfunc='sum', fill_value=0)
    df_pivot.reset_index(inplace=True)
    hio.df_to_csv(df_pivot, fn_property_year_pivot, write_to_excel_too=True, index=True)

    plot_year_property(fn_property_year_pivot, **search.plotting)

    # percentage charts
    data_property_group_property_cnt = Counter()
    data_property_group_property_l = list()
    for property_group, property, year, cnt in data_manual:
        data_property_group_property_cnt[(property_group, property)] += cnt
    for (property_group, property), cnt in data_property_group_property_cnt.items():
        data_property_group_property_l.append([property_group, property, cnt, cnt / len(manual_articles_df)])

    df_percentage = pd.DataFrame(data_property_group_property_l,
                                 columns=['property_group', 'property', 'cnt', 'percentage'])

    fn_percentage = remove_extension(search.file_results_property_group_percentage) + '_manual.csv'
    hio.df_to_csv(df_percentage, fn_percentage)
    plot_property_group_percentage(fn_percentage, max_len=30)

    # heatmap
    if not heatmap_groups:
        heatmap_groups = [property_groups_selected]
    prepare_property_group_properties_counts_df(properties_counter, property_pairs, fn_prop)
    heatmap_graph_data(fn_prop, search, property_group_combinations=heatmap_groups)
