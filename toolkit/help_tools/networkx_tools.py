__author__ = 'eftim'
import networkx as nx
import matplotlib.pyplot as plt
from help_tools import helpers as h
import numpy as np
import matplotlib.colors as colors
from matplotlib.ticker import LogFormatter


def _generate_log_ticks_10(min_color, max_color):
    # values = [min_color]
    # tick = min_color
    values = []
    start_tick = 10 ** (np.ceil(np.log10(min_color)) - 1)
    end_tick = 10 ** (np.ceil(np.log10(max_color)) + 1)
    tick = start_tick
    while tick < end_tick:
        val = np.ceil(np.log10(tick))
        for i in range(10, 20):
            tick = int(10 ** (val * i * 0.1))
            if tick > max_color:
                break
            values.append(tick)
        tick *= 10
    # values.append(max_color)
    return values


def _generate_log_ticks_simple(min_color, max_color):
    values = [min_color, int((min_color + max_color) * 0.5), max_color]
    # values = list(range(min_color, max_color, int((max_color - min_color) / 5.0)))
    # values.append(max_color)
    return values


def _generate_log_ticks_log(min_color, max_color):
    values = list(np.logspace(np.log10(min_color), np.log10(max_color), num=5, endpoint=True, base=10).astype(int))
    # values = sorted(set(values + _generate_log_ticks_10(min_color, max_color)))
    return values


def plot_graph(G: nx.Graph, has_pos=False, dest_file: str = None, labels=False, color='PuRd', title=None,
               node_size_multiplier=1, invert_color=False, graph_type='circular', color_map='log', color_bar=False):
    """

    :param G:
    :param has_pos:
    :param dest_file:
    :param labels:
    :param color: One of the color maps here: https://matplotlib.org/tutorials/colors/colormaps.html
    :param title:
    :return:
    """
    width = 25.6
    width = 20
    height = width * 3 / 4.0  # 25.6, 19.2
    fig, ax = plt.subplots()
    fig = plt.figure(figsize=(width, height))
    # if node_size_multiplier < 1:
    #     G1 = G
    # else:
    mapping = dict(
        [(n, '\n'.join(n.split()) + '\n' + str(w)) for n, w in nx.get_node_attributes(G, 'weight').items()])
    G1 = nx.relabel_nodes(G, mapping=mapping)
    node_colors = ['red' for node in G1.nodes()]
    node_size = 5000 * node_size_multiplier
    # node_colors = list(nx.get_node_attributes(G1, 'weight').values())
    edge_cmap = plt.get_cmap(color)
    edge_colors = [1 + x for x in nx.get_edge_attributes(G1, 'weight').values()]
    min_edge_color, max_edge_color = min(edge_colors), max(edge_colors)
    if color_map == 'log':
        edge_colors = list(np.log10(edge_colors))
    node_cmap = plt.get_cmap('YlOrRd')
    node_colors = list(nx.get_node_attributes(G1, 'weight').values())
    min_node_color, max_node_color = min(node_colors), max(node_colors)
    if color_map == 'log':
        node_colors = list(np.log10(node_colors))

    if invert_color:
        max_weight = max(edge_colors)
        edge_colors = [max_weight - v for v in edge_colors]
    if has_pos:
        pos = nx.get_node_attributes(G1, 'pos')
    else:
        # https://networkx.github.io/documentation/networkx-1.11/reference/generated/networkx.drawing.layout.fruchterman_reingold_layout.html
        # pos = nx.drawing.layout.spring_layout(G1, seed=100, iterations=50, k=1)
        # pos = nx.drawing.layout.shell_layout(G1)
        # pos = nx.drawing.layout.spectral_layout(G1)
        if graph_type == 'circular':
            pos = nx.drawing.layout.circular_layout(G1)
        else:
            pos = nx.drawing.kamada_kawai_layout(G1)
            if len(G.nodes()) > 30:
                k = 2
                iterations = 30
            else:
                k = 5
                iterations = 50
            pos = nx.drawing.layout.spring_layout(G1, pos=pos, seed=100, iterations=iterations, k=k)

    # https://matplotlib.org/tutorials/colors/colormaps.html
    # nx.draw_networkx(G1, pos=pos, node_size=node_size, width=20, alpha=0.8, node_color=node_colors,
    #                  edge_color=edge_colors, with_labels=labels,
    #                  edge_cmap=edge_cmap)
    nx.draw_networkx(G1, pos=pos, node_size=node_size, width=20, alpha=0.8, node_color=node_colors,
                     edge_color=edge_colors, with_labels=labels, cmap=node_cmap,
                     edge_cmap=edge_cmap)

    formatter = LogFormatter(10, labelOnlyBase=False)
    if labels:
        edge_labels = nx.get_edge_attributes(G1, 'weight')
        nx.draw_networkx_edge_labels(G1, pos, edge_labels=edge_labels)
    plt.axis('off')
    node_title = 'Published articles'
    edge_title = 'Edges'
    if title:
        plt.title(title)
        if 'collaborations' in title:
            edge_title = 'Collaborations'
        else:
            edge_title = 'Co-occurrences'
    if color_map == 'log':
        sm = plt.cm.ScalarMappable(cmap=node_cmap, norm=colors.LogNorm(vmin=min_node_color, vmax=max_node_color))
    else:
        sm = plt.cm.ScalarMappable(cmap=node_cmap, norm=plt.Normalize(vmin=min_node_color, vmax=max_node_color))
    sm._A = []
    ticks = _generate_log_ticks_simple(min_node_color, max_node_color)
    if color_bar:
        try:
            cbaxes_nodes = fig.add_axes([0.2, 0.1, 0.25, 0.02])  # Coordinates for the colorbar on the figure
            clb_nodes = plt.colorbar(sm, orientation='horizontal', cax=cbaxes_nodes, format=formatter, ticks=ticks)
            clb_nodes.ax.set_xticklabels(ticks)
            # clb_nodes.ax.minorticks_on()
            clb_nodes.set_label(node_title, fontsize=12)  # , labelpad=-40, y=1.05, rotation=0)
        except Exception as e:
            h.log_line("Error creating colorbar 1:", e)

    if color_map == 'log':
        sm = plt.cm.ScalarMappable(cmap=edge_cmap, norm=colors.LogNorm(vmin=min_edge_color, vmax=max_edge_color))
    else:
        sm = plt.cm.ScalarMappable(cmap=edge_cmap, norm=plt.Normalize(vmin=min_edge_color, vmax=max_edge_color))
    sm._A = []
    if color_bar:
        try:
            cbaxes_edges = fig.add_axes([0.55, 0.1, 0.25, 0.02])  # Coordinates for the colorbar on the figure
            # cb = plt.colorbar(ticks=[1, 5, 10, 20, 50], format=formatter)
            ticks = _generate_log_ticks_simple(min_edge_color, max_edge_color)
            clb_edges = plt.colorbar(sm, orientation='horizontal', cax=cbaxes_edges, ticks=ticks)
            clb_edges.ax.set_xticklabels(ticks)  # horizontal colorbar
            # clb_edges.ax.minorticks_on()
            # clb_edges.update_ticks()
            # clb_edges = plt.colorbar(sm, orientation='horizontal', cax=cbaxes_edges, ticks=[10, 20, 30, 50, 100, 125],
            #                          format=formatter)
            clb_edges.set_label(edge_title, fontsize=12)
        except Exception as e:
            h.log_line("Error creating colorbar 2:", e)

    # plt.show()
    if dest_file:
        dpi = 300 if dest_file.endswith('png') else None
        plt.savefig(dest_file, dpi=dpi)
        if not dest_file.endswith('pdf'):
            plt.savefig(h.remove_extension(dest_file) + '.pdf')
    plt.close('all')


def plot_graph_weighted(G: nx.Graph, has_pos=False, dest_file: str = None, labels=False, title=None):
    plt.figure(figsize=(25.6, 19.2))
    mapping = dict([(n, str(n) + ':' + str(w)) for n, w in nx.get_node_attributes(G, 'weight').items()])
    G1 = nx.relabel_nodes(G, mapping=mapping)
    from collections import defaultdict
    edges_by_weight = defaultdict(list)
    max_edge_weight = 0
    min_edge_weight = None
    for (u, v, d) in G1.edges(data=True):
        edges_by_weight[d['weight']].append((u, v))
        max_edge_weight = max(max_edge_weight, d['weight'])
        if min_edge_weight is None:
            min_edge_weight = d['weight']
        else:
            min_edge_weight = min(min_edge_weight, d['weight'])
    if max_edge_weight == min_edge_weight:
        return plot_graph(G1, has_pos)

    if not min_edge_weight:
        min_edge_weight = max_edge_weight
    nodes_by_weight = defaultdict(list)
    max_node_weight = 0
    min_node_weight = None
    for (u, d) in G1.nodes(data=True):
        try:
            cw = d.get('weight', 1)
            nodes_by_weight[cw].append(u)
            max_node_weight = max(max_node_weight, d['weight'])
            if min_node_weight is None:
                min_node_weight = d['weight']
            else:
                min_node_weight = min(min_node_weight, d['weight'])
        except Exception as ex:
            print(u, type(d), d, ex)
    if not min_node_weight:
        min_node_weight = max_node_weight
    plt.figure(figsize=(14, 10))
    edge_color = 'blue'
    node_color = 'red'
    # edge_colors = [edge_color for e in G1.edges()]
    # node_colors = ['red' for node in G1.nodes()]
    if has_pos:
        pos = nx.get_node_attributes(G1, 'pos')
    else:
        # https://networkx.github.io/documentation/networkx-1.11/reference/generated/networkx.drawing.layout.fruchterman_reingold_layout.html
        pos = nx.drawing.layout.spring_layout(G1, seed=100)
    # edges
    min_line_width = 10.0
    max_line_width = 20.0
    edge_weight_range = float(max_edge_weight - min_edge_weight)
    line_scaler = max_line_width - min_line_width

    for weight, edges in edges_by_weight.items():
        min_max_norm = (weight - min_edge_weight) / edge_weight_range
        line_weight = min_line_width + min_max_norm * line_scaler
        nx.draw_networkx_edges(G1, pos, edgelist=edges, width=line_weight, alpha=0.6, edge_color=edge_color)

    # nodes
    # nx.draw_networkx_nodes(G1, pos, node_color=node_colors, node_size=20)
    min_node_size = 200.0
    max_node_size = 1000.0
    node_weight_range = float(max_node_weight - min_node_weight)
    size_scaler = max_node_size - min_node_size

    for weight, nodes in nodes_by_weight.items():
        min_max_norm = (weight - min_node_weight) / node_weight_range
        node_size = min_node_size + min_max_norm * size_scaler
        nx.draw_networkx_nodes(G1, pos, nodelist=nodes, node_size=node_size, node_color=node_color)
    if labels:
        nx.draw_networkx_labels(G1, pos)
        edge_labels = nx.get_edge_attributes(G1, 'weight')
        nx.draw_networkx_edge_labels(G1, pos, edge_labels=edge_labels)
    plt.axis('off')

    if title:
        plt.title('plot_graph')
    # plt.show()
    if dest_file:
        dpi = 300 if dest_file.endswith('png') else None
        plt.savefig(dest_file, dpi=dpi)
        if not dest_file.endswith('pdf'):
            plt.savefig(h.remove_extension(dest_file) + '.pdf')
    plt.close('all')


def get_colormaps():
    # One of the color maps here: https://matplotlib.org/tutorials/colors/colormaps.html
    cmaps = dict()
    cmaps['Perceptually Uniform Sequential'] = [
        'viridis', 'plasma', 'inferno', 'magma', 'cividis']
    cmaps['Sequential (2)'] = [
        'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
        'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
        'hot', 'afmhot', 'gist_heat', 'copper']
    cmaps['Sequential'] = [
        'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
        'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
        'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn']
    cmaps['Miscellaneous'] = [
        'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
        'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg',
        'gist_rainbow', 'rainbow', 'jet', 'nipy_spectral', 'gist_ncar']
    cmaps['Qualitative'] = ['Pastel1', 'Pastel2', 'Paired', 'Accent',
                            'Dark2', 'Set1', 'Set2', 'Set3',
                            'tab10', 'tab20', 'tab20b', 'tab20c']

    maps = [y for x in cmaps.values() for y in x]
    return maps
