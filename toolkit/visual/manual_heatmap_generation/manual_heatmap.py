from typing import List, Tuple

import numpy as np
import pandas as pd
from collections import defaultdict

from matplotlib import pyplot as plt
import seaborn as sns

from configuration.const import Const
from visual.chart_helpers import load_graph_counts, prepare_property_group_combinations, \
    prepare_property_group_combination_counts


def heatmap_manual_generation(input_filename: str,
                       property_group_combinations: List[Tuple[str]] = None, plot_type='pdf', color_map='log',
                       **kwargs):
    """

    :param input_filename: The file with edge information, typically `filtered_graph_properties.csv`
    :param folder_results:
    :param search:
    :param property_group_combinations:
    :param plot_type:
    :param color_map:
    :param kwargs:
    :return:
    """
    manual_run = True
    properties, properties_edges, property_groups = load_graph_counts(input_filename)

    if not property_group_combinations:
        property_group_combinations = list()
    # Prepare the property group combinations
    prepare_property_group_combinations(property_groups, property_group_combinations)
    for edges, edge_weights, file_suffix in prepare_property_group_combination_counts(properties, properties_edges,
                                                                                      property_groups,
                                                                                      property_group_combinations):
        if len(edges) == 0:  # Skip plotting the graph if there are no edges
            continue

        property_pairs = dict()
        valid_properties = set()
        selected = set()
        valid_prop_groups = dict()
        for property_1, property_2, weight in edges:
            pair_key = tuple(sorted([property_1, property_2]))
            if pair_key in property_pairs:
                continue
            valid_properties.add(property_1)
            valid_properties.add(property_2)
            valid_prop_groups.setdefault(property_1[0], set())
            valid_prop_groups.setdefault(property_2[0], set())
            valid_prop_groups[property_1[0]].add(property_1[1])
            valid_prop_groups[property_2[0]].add(property_2[1])
            property_pairs.setdefault(pair_key, 0)
            selected.add(pair_key)
            property_pairs[pair_key] = weight

            # self-referencing i
            pair_key = tuple(sorted([property_1, property_1]))
            property_pairs.setdefault(pair_key, 0)
            selected.add(pair_key)
            # this makes for a high imbalance
            # property_pairs[pair_key] += 1
            # property_pairs[pair_key] = 1
            property_pairs[pair_key] = np.nan

            # self-referencing i
            pair_key = tuple(sorted([property_2, property_2]))
            property_pairs.setdefault(pair_key, 0)
            selected.add(pair_key)
            # this makes for a high imbalance
            # property_pairs[pair_key] += 1
            # property_pairs[pair_key] = 1
            property_pairs[pair_key] = np.nan

        all_props_full = []
        all_props = []
        n = 0
        printed_properties = set()
        if manual_run:
            # there could be additional properties or property groups that didn't exist in the original run
            for group in valid_prop_groups:
                cnt_new = 0
                for prop in valid_prop_groups[group]:
                    prop_key = (group, prop)
                    if prop_key in printed_properties:
                        continue
                    all_props_full.append(prop_key)
                    all_props.append(prop)
                    cnt_new += 1
                if cnt_new > 0:
                    all_props_full.append(('', ''))  # to make a space between property groups
                    all_props.append('')

        edge_values = []
        for i in range(len(all_props_full)):
            edge_value = []
            for j in range(len(all_props_full)):
                pair_key = tuple(sorted([all_props_full[i], all_props_full[j]]))

                if pair_key in property_pairs:
                    edge_value.append(property_pairs[pair_key])
                elif ('', '') in (all_props_full[i], all_props_full[j]):
                    edge_value.append(np.nan)
                else:
                    edge_value.append(0)
            edge_values.append(edge_value)

        plt.clf()
        df_edges = pd.DataFrame(data=edge_values, columns=all_props, index=all_props)
        mask = df_edges.isnull()  # to hide the cells dividing property groups
        if len(valid_properties) < 10:
            fig_x = fig_y = 45
        elif len(valid_properties) < 30:
            fig_x = fig_y = 55
        elif len(valid_properties) < 40:
            fig_x = fig_y = 60
        else:
            fig_x = fig_y = 65
        # fig_y += 5
        plt.figure(figsize=(fig_x*1.2, fig_y*1.3))
        # cmap = 'Blues'
        cmap = 'YlOrRd'
        if len(valid_properties) < 30:
            font_size = 15
        else:
            font_size = 14
        sns.set_style("ticks", {"xtick.major.length": 0, "ytick.major.length": 0})
        try:
            fmt = ".0f"
            # sns.set(font_scale=1.4)
            h = sns.heatmap(df_edges, mask=mask, square=True, cmap=cmap, annot=True, linewidths=.5, cbar=False, fmt=fmt
                            , annot_kws={"size": font_size}
                            )
        except Exception as e:
            h = sns.heatmap(df_edges, mask=mask, square=True, cmap=cmap, annot=True, linewidths=.5, cbar=False
                            , annot_kws={"size": font_size}
                            )
        h.set_xticklabels(h.get_xmajorticklabels(), fontsize=font_size)
        h.set_yticklabels(h.get_ymajorticklabels(), fontsize=font_size)
        # final_path = os.path.join(search.folder_results, f'{Const.heatmap_dest_filename}_{file_suffix}.{plot_type}')
        final_path = f'{Const.heatmap_dest_filename}_{file_suffix}.{plot_type}'
        dpi = 300 if plot_type == 'png' else None
        plt.savefig(final_path, dpi=dpi)


def count_edges(input_filename: str, columns_of_interest: List[str]):
    df = pd.read_excel(input_filename)
    df_interest = df[columns_of_interest]
    df_interest = df_interest.replace('', 'not available')

    results = []

    property_count = defaultdict(int)
    property_edges_count = defaultdict(lambda: defaultdict(int))

    for _, row in df_interest.iterrows():
        row_properties = {}
        for column in df_interest.columns:
            properties = [prop.strip() for prop in str(row[column]).split(';')]
            row_properties[column] = properties
            for prop in properties:
                # Count each property occurrence
                property_count[prop] += 1

        for group, properties in row_properties.items():
            for prop in properties:
                for other_group, other_properties in row_properties.items():
                    if other_group != group:
                        for other_prop in other_properties:
                            edge_key = f"{group}:{prop}"
                            edge_value = f"{other_group}:{other_prop}"
                            property_edges_count[edge_key][edge_value] += 1

    for key, edges in property_edges_count.items():
        group, prop = key.split(':', 1)
        edges_str = ';'.join([f"{edge}:{count}" for edge, count in edges.items()])
        results.append([group, prop, property_count[prop], edges_str])

    final_df = pd.DataFrame(results, columns=['property_group', 'property', 'count', 'property_edges'])
    final_df = final_df[final_df['property_edges'] != '']
    return final_df


if __name__ == '__main__':
    # generate hetmaps based on an excel file, when no search object is present
    # the source excel from which the heatmap needs to be generated
    input_excel_filename = ''
    # output file for the edge count excel
    output_edge_count_filename = ''
    # list of the columns which are relevant in the excel
    columns_of_interest = []

    property_edges = count_edges(input_excel_filename, columns_of_interest)
    property_edges.to_excel(output_edge_count_filename)

    properties_combinations = []
    heatmap_manual_generation(output_edge_count_filename, properties_combinations)



