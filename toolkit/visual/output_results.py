import matplotlib

from help_tools import helpers as h
from visual.bar_plots import plot_year, plot_source, plot_year_source, plot_year_property_group, plot_year_property, \
    plot_year_keyword, plot_keyword_source, plot_property_group_percentage
from visual.graphs import create_property_graph, create_country_graph, plot_property_graph_filtered, chord_diagram, \
    sankey_adjacent_property_groups_diagram
from visual.heatmap import heatmap_graph_data
from visual.network_metrics_graphs import plot_network_metrics_graphs
from visual.prisma import generate_prisma_plots

matplotlib.use('Agg')

from core.search_config import SearchConfig


def plot_all(search: SearchConfig):
    search.set_status("Plotting", "Starting")
    plot_year(search.file_results_aggr_year, add_lin_coef=search.add_lin_coef, plot_type=search.plot_type,
              capitalize=search.capitalize)
    plot_source(search.file_results_aggr_source, **search.plotting)
    plot_year_source(search.file_results_aggr_source_year_pivot_relevant, **search.plotting)
    plot_year_property_group(search.file_results_aggr_property_group_year_pivot, **search.plotting)
    plot_year_property(search.file_results_aggr_property_year_pivot, **search.plotting)
    plot_year_keyword(search.file_results_aggr_keyword_year_pivot_relevant, **search.plotting)
    plot_keyword_source(search.file_results_aggr_keyword_source_pivot_relevant, **search.plotting)
    plot_property_group_percentage(search.file_results_property_group_percentage)

    create_property_graph(search.file_results_graph_data, search.file_results_graph_plot, **search.plotting)
    create_country_graph(search.file_results_graph_data, search.file_results_graph_plot, **search.plotting)

    #chord_diagram(search.file_results_graph_data, search)
    #sankey_adjacent_property_groups_diagram(search.file_results_graph_data, search)

    generate_prisma_plots(search.file_results_aggr_prisma, **search.plotting)
    # the main heatmap
    heatmap_graph_data(search.file_filtered_graph_properties, search, **search.plotting)
    plot_property_graph_filtered(search.file_filtered_graph_properties, search.folder_results,
                                 **search.plotting)
    try:
        plot_network_metrics_graphs(search.file_results_articles_filtered, search.file_results_aggr_property_year_pivot,
                                    4, **search.plotting)
    except Exception as e:
        h.log_line('Ah toj Jane, ah toj Jane...', search.file_results_articles_filtered,
                   search.file_results_aggr_property_year_pivot, e)
    search.set_status("Plotting")
