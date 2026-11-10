import re
from collections import Counter
from itertools import combinations
from typing import List, Tuple, Set, Dict

import matplotlib
import pandas as pd
from slugify import slugify

from help_tools import hio
from help_tools.helpers import log_line

matplotlib.use('Agg')


def prepare_property_group_combinations(property_groups: Set[str], property_group_combinations: List[Tuple[str]]):
    # Prepare the property group combinations
    n_property_group_combinations: List[int] = []
    n_groups = len(property_groups)
    if len(property_group_combinations) == 0:
        n_property_group_combinations.append(n_groups)
    else:
        exists_full = n_groups in [len(pgc) for pgc in property_group_combinations]
        if not exists_full:
            n_property_group_combinations.append(n_groups)
    for n in n_property_group_combinations:
        property_group_combinations.extend(combinations(property_groups, n))


def prepare_property_group_combination_counts(properties: Dict, properties_edges: Dict,
                                              property_groups: Set[str],
                                              property_group_combinations: List[Tuple[str]] = None):
    l = []
    re_robust = re.compile('[-!@#\s+]')
    properties_robust = {(re_robust.sub('_', prop_group.lower()), prop_group, prop): cnt for (prop_group, prop), cnt in
                         properties.items()}
    for property_group_combination in property_group_combinations:
        # Create the filename for the graph
        if len(property_group_combination) == len(property_groups):
            identifier = 'all_properties'
        else:
            identifier = '_'.join([slugify(prop_group) for prop_group in property_group_combination])

        # Construct all relevant properties and edges for the graph
        property_group_combination = [re_robust.sub('_', prop_group.lower()) for prop_group in
                                      property_group_combination]
        properties_to_use = [(prop_group, prop) for (prop_group_robust, prop_group, prop) in properties_robust if
                             prop_group_robust in property_group_combination]
        edges = list()
        edge_weights = list()
        for property_1 in properties_to_use[:-1]:
            for property_2 in properties_to_use[1:]:
                weight = properties_edges.get(property_1, Counter())[property_2]
                edges.append((property_1, property_2, weight))
                edge_weights.append(weight)
        l.append((edges, edge_weights, identifier))
    return l


def prepare_property_group_properties_counts_df(properties_counter: Counter, property_pairs: Counter,
                                                file_filtered_graph_properties: str = None):
    """
    Create property graph file header and create data frame for the property graph
    :param properties_counter:
    :param property_pairs:
    :return:
    """
    filtered_graph_properties_header = ['property_group', 'property', 'count', 'property_edges']
    filtered_graph_properties = list()
    for element, counter in properties_counter.items():
        property_group, prop = element
        edges = list()
        for (property_pair_1, property_pair_2), count in property_pairs.items():
            if property_pair_1 == element:
                edges.append(':'.join(property_pair_2 + tuple([str(count)])))
            if property_pair_2 == element:
                edges.append(':'.join(property_pair_1 + tuple([str(count)])))
        edges = ';'.join(edges)
        filtered_graph_properties_record = [property_group, prop, counter, edges]
        filtered_graph_properties.append(filtered_graph_properties_record)
    df_filtered_graph_properties = pd.DataFrame(data=filtered_graph_properties,
                                                columns=filtered_graph_properties_header)
    if file_filtered_graph_properties:
        hio.df_to_csv(df_filtered_graph_properties, file_filtered_graph_properties, write_to_excel_too=True)
    return df_filtered_graph_properties


def load_graph_counts(input_filename) -> Tuple[Dict, Dict, Set]:
    df_properties = hio.pd_read_csv_or_excel(filename=input_filename)
    # Prepare dictionaries from the input dataframe
    property_groups = set(df_properties['property_group'])
    properties = dict()
    properties_edges = dict()
    for property_group, prop, count, prop_edges in zip(df_properties['property_group'], df_properties['property'],
                                                       df_properties['count'], df_properties['property_edges']):
        properties[(property_group, prop)] = count
        try:
            properties_pair_counter = Counter({(ppg, pp): int(ppv) for ppg, pp, ppv in
                                               (property_pair.split(':') for property_pair in prop_edges.split(';'))})
            properties_edges[property_group, prop] = properties_pair_counter
        except Exception as e:
            log_line("Exception", property_group, prop, count, prop_edges)
    return properties, properties_edges, property_groups
