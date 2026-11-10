import shutil
from collections import Counter
from itertools import combinations

from configuration.config import Config
from core.search_config import SearchConfig
from help_tools import hio
from visual.bar_plots import *
from visual.graphs import *
from visual.heatmap import *
from visual.prisma import *

matplotlib.use('Agg')
import os

from configuration.const import Const
from visual.chart_helpers import prepare_property_group_properties_counts_df


def process_and_plot_filtered_articles(filtered_articles_filename: str, search_obj: SearchConfig, **kwargs):
    """
    Process filtered articles and re-plot the graphs with the new information

    :param filtered_articles_filename: Filepath where the filtered articles file is located
    :type filtered_articles_filename: str
    :param search_obj: Pre-generated search configuration object
    :type search_obj: SearchConfig
    """

    # Create folder for the new results
    if search_obj is not None:
        graph_results_folder_name = search_obj.folder_results
    else:
        folder_name = os.path.dirname(os.path.realpath(filtered_articles_filename))
        graph_results_folder_name = os.path.join(folder_name, Const.graph_results_folder_name)
    # if os.path.exists(graph_results_folder_name):
    #     archive_old_graph_results(graph_results_folder_name)
    # else:
    #     h.create_folder(graph_results_folder_name)
    if not os.path.exists(graph_results_folder_name):
        h.create_folder(graph_results_folder_name)
    # Read and prepare the filtered articles
    filtered_articles = hio.pd_read_csv_or_excel(filename=filtered_articles_filename)
    filtered_articles.columns = filtered_articles.columns.str.replace(r'[-!@#\s+]', '_', regex=True)  # Empty space name
    filtered_articles_columns = filtered_articles.columns
    summary_header_columns = Config.keywords_summary_header
    property_groups = list(set(filtered_articles_columns) - set(summary_header_columns))

    property_groups_years = {property_group: dict() for property_group in property_groups}
    properties_years = {property_group: dict() for property_group in property_groups}
    properties_counter = Counter()
    property_pairs = Counter()
    keywords = set()
    sources_relevant = Counter()
    years_relevant = Counter()
    keyword_source = dict()
    keyword_year = dict()
    source_year = dict()

    # Process the filtered articles
    for filtered_article in filtered_articles.itertuples():

        # Extract the year from the data frame
        try:
            year = int(getattr(filtered_article, 'year'))
            years_relevant[year] += 1
        except AttributeError:
            h.log_line('Skipping article. Year is not provided.')
            year = None
        except (ValueError, TypeError):
            h.log_line('Skipping article. Invalid year.')
            year = None

        # Extract the keyword and the source from the data frame
        try:
            keyword = getattr(filtered_article, 'keyword')
            keywords.add(keyword)
        except AttributeError:
            keyword = None
        try:
            source = getattr(filtered_article, 'source')
            sources_relevant[source] += 1
        except AttributeError:
            source = None

        # Construct keyword, source, year summaries
        if keyword is not None and source is not None:
            keyword_source.setdefault(keyword, dict())
            keyword_source[keyword][source] = keyword_source[keyword].get(source, 0) + 1
        if keyword is not None and year is not None:
            keyword_year.setdefault(keyword, dict())
            keyword_year[keyword][year] = keyword_year[keyword].get(year, 0) + 1
        if source is not None and year is not None:
            source_year.setdefault(source, dict())
            source_year[source][year] = source_year[source].get(year, 0) + 1

        # Construct property group and property summary
        all_properties = set()
        for property_group in property_groups:
            try:
                properties = getattr(filtered_article, property_group)
                if properties:
                    properties = properties.split(',')
                    if year is not None:
                        property_groups_years.setdefault(property_group, dict())
                        property_groups_years[property_group].setdefault(year, 0)
                        property_groups_years[property_group][year] += 1

                    for prop in properties:
                        properties_counter[(property_group, prop)] += 1
                        all_properties.add((property_group, prop))
                        if year is not None:
                            properties_years.setdefault(property_group, dict())
                            properties_years[property_group].setdefault(prop, dict())
                            properties_years[property_group][prop].setdefault(year, 0)
                            properties_years[property_group][prop][year] += 1
            except AttributeError:
                h.log_line('Skipping article. Invalid properties.')
        for combination in combinations(all_properties, 2):
            key = tuple(sorted(combination))
            property_pairs[key] += 1

    years = sorted(years_relevant)
    sources = sorted(sources_relevant)
    keywords = sorted(keywords)

    # Create property group year file header
    aggregated_property_groups_years_header = ['property_group', 'year', 'article_count']
    aggregated_property_groups_years = list()
    aggregated_property_groups_years_pivot_header = ['property_group'] + [str(year) for year in years]
    aggregated_property_groups_years_pivot = list()

    # Populate property group year file content and create data frames
    for property_group, pg_years in property_groups_years.items():
        property_group_year_pivot_element = [property_group]
        for year in years:
            property_group_year_count = pg_years.get(year, 0)
            property_group_year_element = [property_group, year, property_group_year_count]
            aggregated_property_groups_years.append(property_group_year_element)
            property_group_year_pivot_element.append(property_group_year_count)
        aggregated_property_groups_years_pivot.append(property_group_year_pivot_element)

    df_aggregated_property_group_years = pd.DataFrame(data=aggregated_property_groups_years,
                                                      columns=aggregated_property_groups_years_header)
    df_aggregated_property_group_years_pivot = pd.DataFrame(data=aggregated_property_groups_years_pivot,
                                                            columns=aggregated_property_groups_years_pivot_header)

    # Create property year file header
    aggregated_property_years_header = ['property_group', 'property', 'year', 'article_count']
    aggregated_property_years = list()
    aggregated_property_years_pivot_header = ['property_group', 'property'] + [str(year) for year in years]
    aggregated_property_years_pivot = list()

    # Populate property year file content and create data frames
    for property_group, properties in properties_years.items():
        for prop, p_years in properties.items():
            property_year_pivot_element = [property_group, prop]
            for year in years:
                property_year_count = p_years.get(year, 0)
                property_year_element = [property_group, prop, year, property_year_count]
                aggregated_property_years.append(property_year_element)
                property_year_pivot_element.append(property_year_count)
            aggregated_property_years_pivot.append(property_year_pivot_element)

    df_aggregated_property_years = pd.DataFrame(data=aggregated_property_years,
                                                columns=aggregated_property_years_header)
    df_aggregated_property_years_pivot = pd.DataFrame(data=aggregated_property_years_pivot,
                                                      columns=aggregated_property_years_pivot_header)

    # Create property graph file header and create data frame for the property graph
    df_filtered_graph_properties = prepare_property_group_properties_counts_df(properties_counter, property_pairs)

    # Create headers for keyword, source and year charts
    aggregated_keyword_source_pivot_header = ['keyword'] + list(sources)
    aggregated_keyword_source_pivot = list()
    aggregated_keyword_year_pivot_header = ['keyword'] + [str(year) for year in years]
    aggregated_keyword_year_pivot = list()
    aggregated_source_year_pivot_header = ['source'] + [str(year) for year in years]
    aggregated_source_year_pivot = list()

    # Populate keyword, source, year chart file content and create data frames
    for keyword in keywords:
        keyword_source_element = [keyword] + [keyword_source[keyword].get(source, 0) for source in sources]
        aggregated_keyword_source_pivot.append(keyword_source_element)
        keyword_year_element = [keyword] + [keyword_year[keyword].get(year, 0) for year in years]
        aggregated_keyword_year_pivot.append(keyword_year_element)
    for source in sources:
        source_year_element = [source] + [source_year[source].get(year, 0) for year in years]
        aggregated_source_year_pivot.append(source_year_element)

    df_aggregated_keyword_source = pd.DataFrame(data=aggregated_keyword_source_pivot,
                                                columns=aggregated_keyword_source_pivot_header)
    df_aggregated_keyword_year = pd.DataFrame(data=aggregated_keyword_year_pivot,
                                              columns=aggregated_keyword_year_pivot_header)
    df_aggregated_source_year = pd.DataFrame(data=aggregated_source_year_pivot,
                                             columns=aggregated_source_year_pivot_header)

    # Populate source and year chart file and prisma diagram file and create data frames
    df_sources = None
    df_years = None
    df_prisma = None
    if search_obj is not None:
        df_sources = hio.pd_read_csv_or_excel(filename=search_obj.file_results_aggr_source)
        df_sources[Config.PRISMA_relevant] = df_sources['source'].map(sources_relevant).fillna(0).astype('int')
        df_years = hio.pd_read_csv_or_excel(filename=search_obj.file_results_aggr_year)
        df_years['relevant_articles'] = df_years['year'].map(years_relevant).fillna(0).astype('int')
        df_prisma = hio.pd_read_csv_or_excel(filename=search_obj.file_results_aggr_prisma)
        prisma_update = {'quantitative_synthesis': filtered_articles.shape[0]}
        df_prisma['count'] = df_prisma['metric'].map(prisma_update).fillna(df_prisma['count']).astype('int')

    # Generate file names
    file_aggr_property_group_years = os.path.join(graph_results_folder_name,
                                                  Const.file_results_aggr_property_group_year)
    file_aggr_prop_group_years_pivot = os.path.join(graph_results_folder_name,
                                                    Const.file_results_aggr_property_group_year_pivot)
    file_aggr_property_years = os.path.join(graph_results_folder_name, Const.file_results_aggr_property_year)
    file_aggr_property_years_pivot = os.path.join(graph_results_folder_name,
                                                  Const.file_results_aggr_property_year_pivot)
    file_filtered_graph_properties = os.path.join(graph_results_folder_name, Const.file_filtered_graph_properties)
    file_aggr_keyword_source_pivot = os.path.join(graph_results_folder_name,
                                                  Const.file_results_aggr_keyword_source_pivot_relevant)
    file_aggr_keyword_year_pivot = os.path.join(graph_results_folder_name,
                                                Const.file_results_aggr_keyword_year_pivot_relevant)
    file_aggr_source_year_pivot = os.path.join(graph_results_folder_name,
                                               Const.file_results_aggr_source_year_pivot_relevant)
    file_aggr_source = os.path.join(graph_results_folder_name, Const.file_results_aggr_source)
    file_aggr_year = os.path.join(graph_results_folder_name, Const.file_results_aggr_year)
    file_aggr_prisma = os.path.join(graph_results_folder_name, Const.file_results_aggr_prisma)

    # Writing data into csv and excel files
    data_frames = [df_aggregated_property_group_years, df_aggregated_property_group_years_pivot,
                   df_aggregated_property_years, df_aggregated_property_years_pivot, df_filtered_graph_properties,
                   df_aggregated_keyword_source, df_aggregated_keyword_year, df_aggregated_source_year]
    files = [file_aggr_property_group_years, file_aggr_prop_group_years_pivot, file_aggr_property_years,
             file_aggr_property_years_pivot, file_filtered_graph_properties, file_aggr_keyword_source_pivot,
             file_aggr_keyword_year_pivot, file_aggr_source_year_pivot]
    if search_obj is not None:
        data_frames.extend([df_sources, df_years, df_prisma])
        files.extend([file_aggr_source, file_aggr_year, file_aggr_prisma])
    shutil.copy(filtered_articles_filename, graph_results_folder_name)  # Keep the file graphs are generated from
    for data_frame, file in zip(data_frames, files):
        hio.df_to_csv(data_frame, file, write_to_excel_too=True)

    # Collect all plotting files
    plotting_parameters = search_obj.plotting if search_obj is not None else kwargs

    plot_year_property_group(file_aggr_prop_group_years_pivot, **plotting_parameters)
    plot_year_property(file_aggr_property_years_pivot, **plotting_parameters)
    plot_keyword_source(file_aggr_keyword_source_pivot, **plotting_parameters)
    plot_year_keyword(file_aggr_keyword_year_pivot, **plotting_parameters)
    plot_year_source(file_aggr_source_year_pivot, **plotting_parameters)
    plot_property_graph_filtered(file_filtered_graph_properties, **plotting_parameters)

    if search_obj is not None:
        # TODO: not compatible with this file, we need more data
        # create_country_graph(file_filtered_graph_properties, search_obj.file_results_graph_plot,
        #                      **plotting_parameters)
        create_property_graph(file_filtered_graph_properties, search_obj.file_results_graph_plot,
                              **plotting_parameters)
        plot_source(file_aggr_source, **plotting_parameters)
        plot_year(file_aggr_year, **plotting_parameters)
        plot_prisma(file_aggr_prisma, **plotting_parameters)
        plot_prisma_scoping(file_aggr_prisma, **plotting_parameters)
        heatmap_graph_data(file_filtered_graph_properties, search_obj,
                           **plotting_parameters)
