#!/usr/bin/env python3
import os
from datetime import timedelta

import getopt
import sys
import time
from threading import Lock

from crawlers.springer import springer
from help_tools import helpers as h
from help_tools.helpers import log_line
from core.meta_analysis import crawl_and_analyze
from visual.output_results import plot_all
from core.search_config import SearchConfig
from visual.postprocess_filtered_articles import process_and_plot_filtered_articles


from visual.heatmap import heatmap_graph_data

def test_heatmap():
    df = pd_read_csv_or_excel('/Users/eftim/Repositories/article-analysis/data/TestQuery_20220712/results/aggr_property_year.xlsx')
    df_pivot = pd.pivot_table(df, values='cnt', index=['property_group', 'property'], columns='year',
                              aggfunc='sum')
    df_to_csv(df_pivot, '/Users/eftim/Repositories/article-analysis/data/TestQuery_20220712/results/aggr_property_year_piv_eft.csv', write_to_excel_too=True)
    search = SearchConfig.load_object(
        '/Users/eftim/Downloads/results_GoodBrother_Mladjan_20220807_3/search_data_original.json')
    fn_prop = '/Users/eftim/Repositories/article-analysis/data/TestQuery_20220712/results/filtered_graph_properties.xlsx'
    heatmap_graph_data(fn_prop, search.folder_results, **search.plotting)
    search = SearchConfig.load_object(
        '/Users/eftim/Downloads/results_GoodBrother_Mladjan_20220807_3/search_data_original.json')
    lock = Lock()
    springer._scrape_article_page(search, "https://link.springer.com/chapter/10.1007/978-3-658-29726-8_11", lock, keyword = "Assisted living")

if __name__ == "__main__":
    #  -g /Users/eftim/Repositories/article-analysis/data/TestQuery_20220712/filtered_articles_manual_eftim.xlsx
    # -f /Users/eftim/Repositories/article-analysis/data/TestQuery_20220712/ --multithread=true -g /Users/eftim/Repositories/article-analysis/data/TestQuery_20220712/filtered_articles_manual_eftim.xlsx
    test_heatmap()
