import os

from core.search_config import SearchConfig
from core.search_engine import process_manually_analyzed_files, process_articles

if __name__ == '__main__':
    # filename_manually_selected = r'C:\Users\PC\Documents\GitHub\article-analysis\data\Ivan_10mwt_20221024\results\selected_papers_manuallly_10mwt.xlsx'
    # filename_manually_selected = '/Users/eftim/Repositories/article-analysis/data/Ivan_10mwt_20221024/selected_papers_manuallly_10mwt_EZ.xlsx'
    # filename_manually_selected = '/Users/eftim/Repositories/article-analysis/data/Ivan_healthcare_monitoring_20221108/JPB_articles_32_v2.xlsx'
    # filename_manually_selected = '/Users/eftim/Repositories/article-analysis/data/Ivan_healthcare_monitoring_20221108/32_articles_table_V100.xlsx'
    # filename_manually_selected = '/Users/eftim/Repositories/article-analysis/data/Ivan_10mwt_20221024/selected_papers_manuallly_10mwt_EZ_IP.xlsx'
    # filename_manually_selected = '/Users/eftim/Repositories/article-analysis/data/Ivan_10mwt_20221024/selected_papers_manuallly_10mwt_EZ_IP_V2.xlsx'
    # filename_manually_selected = '/Users/eftim/Repositories/article-analysis/data/Ivan_functional_reach_test_20221010/Miudos_Leiria.xlsx'
    # filename_manually_selected = '/Users/eftim/Repositories/article-analysis/data/GoodBrother_datasets_20230215/filtered_articles_GoodBrother_datasets_TODO.xlsx'
    # filename_json = '/Users/eftim/Repositories/article-analysis/data/Ivan_healthcare_monitoring_20221108/search_data.json'
    # filename_json = '/Users/eftim/Repositories/article-analysis/data/Ivan_10mwt_20221024/search_data.json'
    # filename_json = '/Users/eftim/Repositories/article-analysis/data/Ivan_functional_reach_test_20221010/search_data.json'

    filename_manually_selected = '/home/eftim/crawler/article-analysis/Hrvoje_20241031/manually_selected.xlsx'
    filename_json = '/home/eftim/crawler/article-analysis/data/Hrvoje_20241031/search_data.json'

    # Study	Year	Location	Population	Purpose	Methods	Sensors	Disease
    # filename_json = '/Users/eftim/Repositories/article-analysis/data/GoodBrother_datasets_20230215/search_data.json'
    # property_groups = ['Sensors Used', 'Type of Methods', 'Methods', 'Features', 'Type of Communication']
    # property_groups = ['Sensors Used', 'Type of Methods', 'Methods', 'Features', 'Type of Diseases', 'Diseases']
    # property_groups = ['Location', 'Population', 'Purpose',  'Methods', 'Sensors', 'Disease']
    # property_groups = ['Acquisition Platform', 'Action focus', 'Location-Space', 'Problem', 'Resources', 'Type of action']
    # heatmap_groups = [['Sensors Used', 'Type of Methods'],
    #                   ['Type of Methods', 'Methods'],
    #                   ['Features', 'Methods'],
    #                   ['Sensors Used', 'Type of Methods', 'Methods', 'Features', 'Type of Communication']]
    # heatmap_groups = [['Sensors Used', 'Type of Methods'],
    #                   ['Type of Methods', 'Methods'],
    #                   ['Features', 'Methods'],
    #                   ['Type of Methods', 'Type of Diseases'],
    #                   ['Sensors Used', 'Type of Diseases'],
    #                   ['Diseases', 'Type of Diseases'],
    #                   ['Sensors Used', 'Diseases'],
    #                   ['Sensors Used', 'Type of Methods', 'Methods', 'Features', 'Type of Diseases', 'Diseases']]
    # heatmap_groups = [['Sensors', 'Disease'],
    #                   ['Location', 'Sensors'],
    #                   ['Sensors', 'Methods'],
    #                   ['Methods', 'Diseases'],
    #                   ['Location', 'Methods', 'Sensors', 'Disease']]
    # heatmap_groups = [
    #                 ['Acquisition Platform', 'Location-Space'],
    #                 ['Action focus', 'Type of action'],
    #                 ['Problem', 'Resources'],
    #                 ['Acquisition Platform', 'Action focus', 'Location-Space', 'Problem', 'Resources', 'Type of action']]
    # manually_selected_columns = ['Type of Methods', 'Methods', 'Features', 'Diseases']
    # "diseases" and "features", "diseases" and "methods", and "methods" and "features"?

    # dir_path = os.path.dirname(filename_manually_selected)
    # process_manually_analyzed_files(filename_json, filename_manually_selected, property_groups, heatmap_groups)
    search = SearchConfig.prepare_search_object(filename_json)
    process_articles(search=search, file_manually_filtered_articles=filename_manually_selected)
    # heatmap_manually_selected(filename_dir=dir_path, filename_selected=filename_manually_selected,
    #                           property_group_selected=manually_selected_columns)
