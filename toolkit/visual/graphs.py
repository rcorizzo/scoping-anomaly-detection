from collections import OrderedDict
from typing import List, Tuple

import holoviews as hv
import matplotlib
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from holoviews import opts, dim

from core.search_config import SearchConfig
from help_tools import helpers as h
from help_tools import networkx_tools as nxt
from help_tools.browser_emulate import create_chrome_browser

matplotlib.use('Agg')
import os

import numpy as np

from configuration.const import Const
from visual.chart_helpers import prepare_property_group_combinations, prepare_property_group_combination_counts, \
    load_graph_counts


def plot_property_graph_filtered(input_filename: str, results_folder_name: str = None,
                                 property_group_combinations: List[Tuple[str]] = None,
                                 plot_type='pdf', color_map='log',
                                 **kwargs):
    """
    Plot multiple property spring graphs and store them in a separate folder which is inside the parent folder of the
    input filename
    If property group combinations is specified, then we create a separate graph for each property group combination.
    Otherwise, we use the n property group combinations parameter which tells us the length of the tuples to generate
    as a property group combinations

    :param input_filename: Filename for the input file that helps construct the property spring graphs
    :type input_filename: str
    :param property_group_combinations: Combinations of property groups for which we want to create a graph
    :type property_group_combinations: List[Tuple[str]]
    :param plot_type: The extension that we want to save the graphs with
    :type plot_type: str
    :param color_map: Color map for the graph
    :type color_map: str
    """
    try:
        properties, properties_edges, property_groups = load_graph_counts(input_filename)

        if not property_group_combinations:
            property_group_combinations = list()
        # Prepare the property group combinations
        prepare_property_group_combinations(property_groups, property_group_combinations)

        # Create folder for all graphs that are going to be plotted
        folder_name = os.path.dirname(os.path.realpath(input_filename))
        if not results_folder_name and not os.path.exists(results_folder_name):
            results_folder_name = os.path.join(folder_name, Const.graph_results_folder_name)
            h.create_folder(results_folder_name)
        for edges, edge_weights, file_suffix in prepare_property_group_combination_counts(properties, properties_edges,
                                                                                          property_groups,
                                                                                          property_group_combinations):
            if len(edges) == 0:  # Skip plotting the graph if there are no edges
                continue

            # Filter the edges and the properties based on a threshold
            G = nx.Graph()
            threshold_percentile = 0 if len(edge_weights) < 100 else 75
            edge_weights_threshold = int(np.percentile(edge_weights, threshold_percentile))
            selected_properties = set()
            for property_1, property_2, weight in edges:
                if property_1[1] == property_2[1]: continue
                if weight >= edge_weights_threshold:
                    G.add_edge(property_1[1], property_2[1], weight=weight)
                    selected_properties.add(property_1)
                    selected_properties.add(property_2)

            if len(selected_properties) < 2:  # Skip plotting the graph if there are not enough properties
                continue

            for selected_property in selected_properties:
                weight = properties.get(selected_property, 0)
                G.add_node(selected_property[1], weight=weight)

            # Plot the graph
            title = 'Shown keywords:{0} Shown pairs: {1} Minimum co-occurrence in articles: {2}' \
                    ' ({3}-th percentile)'.format(len(G.nodes()), len(G.edges),
                                                  edge_weights_threshold, threshold_percentile)
            final_path = os.path.join(results_folder_name, f'{Const.property_graph_filename}_{file_suffix}.{plot_type}')
            nxt.plot_graph(G, dest_file=final_path, labels=True, title=title, graph_type='spring',
                           node_size_multiplier=1, color_map=color_map)
            nx.write_gml(G, h.remove_extension(final_path) + '.gml')
    except Exception as e:
        h.log_line('Unable to plot graph.', e)
    plt.close('all')


def create_property_graph(filename: str, filename_plot: str,
                          plot_type='pdf', color_map='log', **kwargs):
    try:
        articles = pd.read_csv(filename, sep='\t', index_col=0, header=0)
        G = nx.Graph()
        property_pairs = OrderedDict()
        properties = {}
        for index, row in articles.iterrows():
            vals = row['properties'].split(';')
            found_props = []
            for prop in vals:
                found_props.append(prop)
                properties.setdefault(prop, 0)
                properties[prop] += 1
            found_props.sort()
            for i in range(len(found_props) - 1):
                for j in range(i + 1, len(found_props)):
                    pair_key = (found_props[i], found_props[j])
                    property_pairs.setdefault(pair_key, 0)
                    property_pairs[pair_key] += 1

        edge_weights = list(property_pairs.values())
        if len(edge_weights) < 100:
            thr_percentile = 0
        else:
            thr_percentile = 75
        edge_weights_thres = int(np.percentile(edge_weights, thr_percentile))
        selected_properties = set()
        for (property1, property2), weight in property_pairs.items():
            if weight >= edge_weights_thres:
                selected_properties.add(property1)
                selected_properties.add(property2)
                G.add_edge(property1, property2, weight=weight)

        for prop, weight in properties.items():
            if prop in selected_properties:
                G.add_node(prop, weight=weight)

        nx.write_gml(G, filename_plot + '_properties.gml')
        title = 'Shown keywords:{0} Shown pairs: {1} Minimum co-occurrence in articles: {2} ({3}-th percentile)'.format(
            len(G.nodes()), len(G.edges), edge_weights_thres, thr_percentile)
        fn_suffix = '_all_properties'
        nxt.plot_graph(G, dest_file=filename_plot + fn_suffix + '.' + plot_type, labels=True, title=title,
                       graph_type='spring', node_size_multiplier=1, color_map=color_map)
        nx.write_gml(G, filename_plot + fn_suffix + '.gml')
        df1 = pd.DataFrame(list(properties.items()), columns=['property', 'weight'])
        df1.to_csv(filename_plot + fn_suffix + '_nodes.csv', index=False, sep='\t')
        df2 = pd.DataFrame(list([(k[0], k[1], v) for k, v in property_pairs.items()]),
                           columns=['property1', 'property2', 'weight'])
        df2.to_csv(filename_plot + fn_suffix + '__edges.csv', index=False, sep='\t')
    except Exception as e:
        h.log_line('Unable to plot graph.', e)
    plt.close('all')


def create_country_graph(filename: str, filename_plot: str,
                         max_countries=50, plot_type='pdf', color_map='log', **kwargs):
    try:
        articles = pd.read_csv(filename, sep='\t', index_col=0, header=0)
        articles.dropna(subset=['countries'], inplace=True)
        G = nx.Graph()
        country_pairs = OrderedDict()
        countries = {}
        countries_collab = {}
        for index, row in articles.iterrows():
            vals = row['countries'].split(';')
            found_countries = []
            for country in vals:
                found_countries.append(country)
                countries.setdefault(country, 0)
                countries[country] += 1
                countries_collab.setdefault(country, 0)
            found_countries.sort()
            for i in range(len(found_countries) - 1):
                for j in range(i + 1, len(found_countries)):
                    pair_key = (found_countries[i], found_countries[j])
                    country_pairs.setdefault(pair_key, 0)
                    country_pairs[pair_key] += 1
                    countries_collab[pair_key[0]] += 1
                    countries_collab[pair_key[1]] += 1
        top_countries = sorted(countries_collab.items(), key=lambda x: x[1], reverse=True)
        top_countries = set([k[0] for k in top_countries[:max_countries]])
        selected_pairs = dict([((u, v), w) for ((u, v), w) in country_pairs.items() if
                               u in top_countries and v in top_countries])
        # collab_perc = 85
        collab_perc = 90
        lst_values = list(selected_pairs.values())
        if len(lst_values) < 100:
            collab_perc = 0
        else:
            collab_perc = 90
        collab_threshold = int(np.percentile(lst_values, collab_perc))
        shown_countries = set()
        # collab_threshold = int(np.percentile(list(country_pairs.values()), 95))
        for (country1, country2), weight in selected_pairs.items():
            if weight >= collab_threshold:
                shown_countries.add(country1)
                shown_countries.add(country2)
                G.add_edge(country1, country2, weight=weight)
        for country in shown_countries:
            G.add_node(country, weight=countries[country])
        title = 'Shown countries:{0} Shown pairs: {1} Minimum collaborations: {2} ({3}-th percentile)'.format(
            len(G.nodes()), len(G.edges),
            collab_threshold, collab_perc)
        # nxt.plot_graph(G, dest_file=filename_plot + '_countries_circular.' + plot_type, labels=True,
        #                node_size_multiplier=0.5, graph_type='circular', title=title)
        fn_suffix = '_all_countries'
        nxt.plot_graph(G, dest_file=filename_plot + fn_suffix + '.' + plot_type, labels=True,
                       node_size_multiplier=0.5, graph_type='spring', title=title, color_map=color_map)
        nx.write_gml(G, filename_plot + fn_suffix + '.gml')
        df1 = pd.DataFrame(list(countries.items()), columns=['property', 'weight'])
        df1.to_csv(filename_plot + fn_suffix + '_nodes.csv', index=False, sep='\t')
        df2 = pd.DataFrame(list([(k[0], k[1], v) for k, v in country_pairs.items()]),
                           columns=['property1', 'property2', 'weight'])
        df2.to_csv(filename_plot + fn_suffix + '_edges.csv', index=False, sep='\t')
    except Exception as e:
        h.log_line('Unable to plot graph.', e)
    plt.close('all')


def chord_diagram(filename: str, search: SearchConfig):
    try:
        articles = pd.read_csv(filename, sep='\t', index_col=0, header=0)
        browser = create_chrome_browser(download_dir=search.folder_repo)
        # property_pairs = {}
        # properties = {}
        # selected = set()
        # all_props = set()

        search_data = search.search_data
        property_lookup = {}
        num = 0
        prop_num = {}
        for group in search_data['properties']:
            property_group = group['property_group']
            synonyms = group['synonyms']
            for synonym in synonyms:
                for s in synonym:
                    prop_num[s] = num
                    num += 1
                    synonym_dict = {'group': property_group, 'name': s}
                    property_lookup[s] = property_group

        for prop_group in search.property_groups:
            property_pairs = {}
            properties = {}
            selected = set()
            all_props = set()
            for index, row in articles.iterrows():
                vals = []
                if type(row['properties']) is str:
                    vals = row['properties'].split(';')
                found_props = []
                for prop in vals:
                    if property_lookup[prop] == prop_group:
                        all_props.add(prop)
                        found_props.append(prop)
                        properties.setdefault(prop, 0)
                        properties[prop] += 1
                found_props.sort()
                for i in range(len(found_props) - 1):
                    for j in range(i + 1, len(found_props)):
                        pair_key = (found_props[i], found_props[j])
                        property_pairs.setdefault(pair_key, 0)
                        selected.add(pair_key)
                        property_pairs[pair_key] += 1

            all_props = list(all_props)
            edge_values = []
            for i in range(len(all_props)):
                edge_value = []
                for j in range(len(all_props)):
                    if (all_props[i], all_props[j]) in property_pairs:
                        edge_value.append(property_pairs[(all_props[i], all_props[j])])
                    elif (all_props[j], all_props[i]) in property_pairs:
                        edge_value.append(property_pairs[(all_props[j], all_props[i])])
                    elif all_props[i] == all_props[j]:
                        edge_value.append(1)
                    else:
                        edge_value.append(0)
                edge_values.append(edge_value)

            df_edges = pd.DataFrame(data=edge_values, columns=all_props, index=all_props)

            data = hv.Dataset((list(df_edges.columns), list(df_edges.index), df_edges),
                              ['source', 'target'], 'value').dframe()
            data = data[data['value'] > 1]
            hv.extension("bokeh")
            hv.opts(height=1300, width=1300)
            chord = hv.Chord(data)
            chord.opts(cmap='Category20', edge_cmap='Category20', width=1500, height=900,
                       edge_color=dim('source').str(), labels='index',
                       node_color=dim('index').str())
            dest_filename = h.remove_extension(filename)
            dest = dest_filename + '_' + prop_group + '_chord_diagram'
            dest = dest.replace('/', '_')

            hv.save(chord, dest, fmt='html', webdriver=browser, backend='bokeh')
            # This is commented because it automatically opens the chord figure that is created while the code is running
            # cc = show(hv.render(chord))

        property_pairs = {}
        properties = {}
        selected = set()
        all_props = set()

        for index, row in articles.iterrows():
            vals = []
            if type(row['properties']) is str:
                vals = row['properties'].split(';')
            found_props = set()
            for prop in vals:
                all_props.add(property_lookup[prop])
                found_props.add(property_lookup[prop])
                properties.setdefault(property_lookup[prop], 0)
                properties[property_lookup[prop]] += 1
            found_props = sorted(found_props)
            if len(found_props) > 1:
                for i in range(len(found_props) - 1):
                    for j in range(i + 1, len(found_props)):
                        pair_key = (found_props[i], found_props[j])
                        property_pairs.setdefault(pair_key, 0)
                        selected.add(pair_key)
                        property_pairs[pair_key] += 1

        all_props = sorted(all_props)
        edge_values = []
        for i in range(len(all_props)):
            edge_value = []
            for j in range(len(all_props)):
                if (all_props[i], all_props[j]) in property_pairs:
                    edge_value.append(property_pairs[(all_props[i], all_props[j])])
                elif (all_props[j], all_props[i]) in property_pairs:
                    edge_value.append(property_pairs[(all_props[j], all_props[i])])
                else:
                    edge_value.append(0)
            edge_values.append(edge_value)

        df_edges = pd.DataFrame(data=edge_values, columns=all_props, index=all_props)

        data = hv.Dataset((list(df_edges.columns), list(df_edges.index), df_edges),
                          ['source', 'target'], 'value').dframe()
        hv.extension("bokeh")
        hv.opts(height=1300, width=1300)
        chord = hv.Chord(data)
        chord.opts(cmap='Category20', edge_cmap='Category20', width=1500, height=900, edge_color=dim('source').str(),
                   labels='index',
                   node_color=dim('index').str())
        dest_filename = h.remove_extension(filename)
        dest = dest_filename + '_global' + '_chord_diagram'

        hv.save(chord, dest, fmt='html', webdriver=browser, backend='bokeh')
        # # This is commented because it automatically opens the chord figure that is created while the code is running
        # cc = show(hv.render(chord))
    except Exception as e:
        h.log_line("Unable to create the chord chart", e)


def sankey_adjacent_property_groups_diagram(filename: str, search: SearchConfig):
    articles = pd.read_csv(filename, sep='\t', index_col=0, header=0)
    browser = create_chrome_browser(download_dir=search.folder_repo)
    property_lookup = {}
    num = 0
    prop_num = {}
    for group in search.search_data['properties']:
        property_group = group['property_group']
        synonyms = group['synonyms']
        for synonym in synonyms:
            for s in synonym:
                prop_num[s] = num
                num += 1
                property_lookup[s] = property_group

    graph_property_pairs = {}
    nodes = set()
    for i in range(len(search.search_data['properties']) - 1):
        left_properties_group = search.search_data['properties'][i]['property_group']
        right_properties_group = search.search_data['properties'][i + 1]['property_group']
        # graph_property_pairs = {}
        for index, row in articles.iterrows():
            vals = []
            found_props = []
            if type(row['properties']) is str:
                vals = row['properties'].split(';')
            for prop in vals:
                found_props.append(prop)
            found_props = sorted(found_props)
            for i in range(len(found_props) - 1):
                for j in range(len(found_props)):
                    if found_props[i] != found_props[j]:
                        if (property_lookup[found_props[i]] == left_properties_group and property_lookup[
                            found_props[j]] == right_properties_group):
                            nodes.add(found_props[i])
                            nodes.add(found_props[j])
                            pair_key = (found_props[i], found_props[j])
                            graph_property_pairs.setdefault(pair_key, 0)
                            graph_property_pairs[pair_key] += 1

                        if (property_lookup[found_props[j]] == left_properties_group and property_lookup[
                            found_props[i]] == right_properties_group):
                            nodes.add(found_props[i])
                            nodes.add(found_props[j])
                            pair_key = (found_props[j], found_props[i])
                            graph_property_pairs.setdefault(pair_key, 0)
                            graph_property_pairs[pair_key] += 1

    values = []
    sources = []
    targets = []
    for key in graph_property_pairs.keys():
        sources.append(key[0])
        targets.append(key[1])
        values.append(graph_property_pairs[key])

    nodes = hv.Dataset(enumerate(nodes), 'index', 'label')
    nums = sources + targets
    d = {ni: indi for indi, ni in enumerate(set(nums))}
    edges = []
    for key in graph_property_pairs.keys():
        edges.append((d[key[0]], d[key[1]], graph_property_pairs[key]))

    sank = hv.Sankey((edges, nodes), ['From', 'To'])

    sank.opts(
        opts.Sankey(labels='label', label_position='right', width=2500, height=1900, cmap='Set1',
                    edge_color=dim('To').str(), node_color=dim('index').str()))

    dest_filename = h.remove_extension(filename)
    dest = dest_filename + '_sankey_adjacent_property_groups' + '.html'

    hv.save(sank, dest, fmt='html', webdriver=browser, backend='bokeh')

    combinations = search.search_data['plotting']['property_group_combinations']
    for combination in combinations:
        graph_property_pairs = {}
        nodes = set()
        for i in range(len(combination) - 1):
            left_properties_group = combination[i]
            right_properties_group = combination[i + 1]
            for index, row in articles.iterrows():
                vals = []
                found_props = []
                if type(row['properties']) is str:
                    vals = row['properties'].split(';')
                for prop in vals:
                    found_props.append(prop)
                found_props = sorted(found_props)
                for k in range(len(found_props) - 1):
                    for j in range(len(found_props)):
                        if found_props[k] != found_props[j]:
                            if (property_lookup[found_props[k]] == left_properties_group and property_lookup[
                                found_props[j]] == right_properties_group):
                                nodes.add(found_props[k])
                                nodes.add(found_props[j])
                                pair_key = (found_props[k], found_props[j])
                                graph_property_pairs.setdefault(pair_key, 0)
                                graph_property_pairs[pair_key] += 1

                            if (property_lookup[found_props[j]] == left_properties_group and property_lookup[
                                found_props[k]] == right_properties_group):
                                nodes.add(found_props[k])
                                nodes.add(found_props[j])
                                pair_key = (found_props[j], found_props[k])
                                graph_property_pairs.setdefault(pair_key, 0)
                                graph_property_pairs[pair_key] += 1

        values = []
        sources = []
        targets = []
        for key in graph_property_pairs.keys():
            sources.append(key[0])
            targets.append(key[1])
            values.append(graph_property_pairs[key])

        nodes = hv.Dataset(enumerate(nodes), 'index', 'label')
        nums = sources + targets
        d = {ni: indi for indi, ni in enumerate(set(nums))}
        edges = []
        for key in graph_property_pairs.keys():
            edges.append((d[key[0]], d[key[1]], graph_property_pairs[key]))

        if edges and nodes:
            sank = hv.Sankey((edges, nodes), ['From', 'To'])

            sank.opts(
                opts.Sankey(labels='label', label_position='right', width=2100, height=1500, cmap='Set1',
                            edge_color=dim('To').str(), node_color=dim('index').str()))

            dest_filename = h.remove_extension(filename)
            dest = dest_filename + '_sankey_' + str(combinations.index(combination)) + '.html'

            hv.save(sank, dest, fmt='html', webdriver=browser, backend='bokeh')

    #
    # numbers = sources + targets
    # d = {ni: indi for indi, ni in enumerate(set(numbers))}
    # sources_num = [d[ni] for ni in sources]
    # targets_num = [d[ni] for ni in targets]
    # fig = go.Figure(data=[go.Sankey(
    #     node=dict(
    #         pad=15,
    #         thickness=20,
    #         line=dict(color="black", width=0.5),
    #         label=numbers,
    #         color="blue"
    #     ),
    #     link=dict(
    #         source=sources_num,
    #         target=targets_num,
    #         value=values
    #     ))])
    #
    # fig.update_layout(font=dict(size=10, color='white'),
    #                   plot_bgcolor='black',
    #                   paper_bgcolor='black')
    #
    # dest_filename = h.remove_extension(filename)
    # dest = dest_filename + '_sankey_' + left_properties_group + '_' + right_properties_group + '.html'
    # fig.write_html(dest)
