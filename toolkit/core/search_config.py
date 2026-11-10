from __future__ import annotations

import datetime
import json
import os
from collections import OrderedDict
from typing import Dict, Any, Optional, List

import pandas as pd

from configuration.config import Config
from configuration.const import Const
from help_tools import helpers as h, hio
from help_tools.tools import tools


class SearchConfig(object):
    def __init__(self, filename=None):
        self.search_data = {}
        self.input_filename = filename
        self.folder_data = None
        self._filename_json = Const.filename_json
        self._filename_pickle = Const.filename_pickle
        self._property_groups = None
        self._property_groups_sorted = None
        self._main_folder_path = None
        self._properties_mandatory_internal = None
        self.status = dict()  # set statuses of different processing steps
        self.status_long = dict()  # set statuses of different processing steps

        self.keywords = []
        # the complication is so each dict can be deserialized in a C# class for the backend
        self.properties = []  # [{"property_group":"", "synonyms":[]}]
        self._properties_mandatory = []
        self.libraries = {}
        self.properties_mandatory_stemmed = []
        self.properties_excluded_stemmed = []
        self.properties_stemmed = []
        self.keyword_lookup = {}
        self.property_lookup = {}  # lookup between a property to all property groups that contain it
        self.property_stem_lookup = {}
        self.property_stem_lookup_tuple = {}  # map between a stemmed property typle, and a set of all property groups that contain it
        self.stem_source_lookup = {}
        self.stem_source_lookup_tuple = {}
        self.properties_major = None
        self.property_synonym_lookup = {}
        self.stemmed_properties = {}
        self.stem_to_property_map = {}
        self.result_files = set()
        self.result_counts = {}
        self.__search_input_text = None
        self.parsing_errors_articles = []
        self.delete_cache = False
        self.set_parameters()
        self.set_result_counts()
        self.create_folders()
        h.log_line('Creating search object for:', self.folder_data, 'start:', self.start_year, 'end:', self.end_year)

    def set_status(self, key: str, value: str = None):
        if value is None:
            value = 'Completed'
        self.status[key] = [h.timestamp(), value]
        self.status_long.setdefault(key, [])
        self.status_long[key].append([h.timestamp(), value])
        self.save_status()

    def search_input_text(self, to_file=False) -> str:
        if to_file:
            return self.search_input_text_internal(to_file=True)
        else:
            if not self.__search_input_text:
                self.__search_input_text = self.search_input_text_internal(to_file=False)
            return self.__search_input_text

    @property
    def calculate_similarities(self):
        return bool(self.search_data.get('calculate_similarities', True))

    @property
    def force_crawl(self):
        return self.search_data.get("force_crawl", False)

    def search_input_text_internal(self, to_file=False) -> str:
        if to_file:
            or_separator = ' OR '
            and_separator = ' AND \n\t'
            keywords_text = "Keywords:\n\t" + ' OR\n\t'.join(self.keywords) + '\n\n'
            open_parenthesis = '('
            close_parenthesis = ')'
        else:
            or_separator = ', '
            and_separator = '. \n\t'
            keywords_text = '.\n'.join(self.keywords) + '\n\n'
            open_parenthesis = ''
            close_parenthesis = ''

        property_groups_synonyms = [(prop_group['property_group'], prop_group['synonyms']) for prop_group in
                                    self.properties]
        search_data_properties = []
        for property_group, properties_within_group in property_groups_synonyms:
            current_search_data_properties = [property_group + ':']
            for property_synonyms in properties_within_group:
                property_synonyms_str = or_separator.join(property_synonyms)
                current_search_data_properties.append('\t' + property_synonyms_str + '.')
            search_data_properties.append('\n'.join(current_search_data_properties))
        properties_text = '\n'.join(search_data_properties) + '\n\n'
        mandatory_properties = []
        for properties_mandatory_OR_conditions in self.properties_mandatory:
            mandatory_group_OR = open_parenthesis + or_separator.join(
                properties_mandatory_OR_conditions) + close_parenthesis
            mandatory_properties.append(mandatory_group_OR)
        mandatory_properties_text = and_separator.join(mandatory_properties)

        if to_file:
            properties_text = "Properties:\n" + properties_text
            mandatory_properties_text = 'Properties mandatory:\n\t' + mandatory_properties_text
            excluded_properties_text = ' OR '.join(self.properties_excluded)
            excluded_properties_text = '\n\nExcluded papers that contain:\n\t' + excluded_properties_text
        else:
            excluded_properties_text = ''
        return keywords_text + properties_text + mandatory_properties_text + excluded_properties_text

    @property
    def search_data(self):
        return self._search_data

    @search_data.setter
    def search_data(self, value):
        self._search_data = value

    def is_library_enabled(self, library_key: str) -> bool:
        return self.search_data.get("libraries", {}).get(library_key.lower(), False)

    def set_library_enabled(self, library_key: str, enabled: bool = True):
        self.search_data.setdefault("libraries", {})
        if enabled is not None:
            self.search_data["libraries"][library_key] = enabled

    @property
    def apply_stemming(self):
        return self.search_data.get("apply_stemming", True)

    @apply_stemming.setter
    def apply_stemming(self, value: bool):
        if value is not None:
            self.search_data["apply_stemming"] = value

    @property
    def remove_stopwords(self):
        return self.search_data.get("remove_stopwords", True)

    @remove_stopwords.setter
    def remove_stopwords(self, value: bool):
        if value is not None:
            self.search_data["remove_stopwords"] = value


    @property
    def apply_phrase_permutations(self):
        return self.search_data.get("apply_phrase_permutations", True)

    @apply_phrase_permutations.setter
    def apply_phrase_permutations(self, value: bool):
        if value is not None:
            self.search_data["apply_phrase_permutations"] = value

    @property
    def plotting(self) -> Dict[str, Any]:
        return self.search_data.get("plotting", dict())

    @property
    def plot_type(self) -> str:
        s = self.plotting.get("plot_type", "pdf").lower()
        if s not in ("png", "pdf"):
            return "pdf"
        else:
            return s

    @plot_type.setter
    def plot_type(self, value: str):
        if value is not None:
            self.search_data.setdefault("plotting", dict())["plot_type"] = value.lower()

    @property
    def add_lin_coef(self) -> bool:
        return self.plotting.get("add_lin_coef", False)

    @property
    def multithread(self) -> bool:
        return self.search_data.get("multithread", True)

    @multithread.setter
    def multithread(self, value: bool):
        self.search_data.setdefault("multithread", True)
        if value is not None:
            self.search_data["multithread"] = value

    @add_lin_coef.setter
    def add_lin_coef(self, value: bool):
        if value is not None:
            self.search_data.setdefault("plotting", dict())["add_lin_coef"] = value

    @property
    def capitalize(self) -> bool:
        """Whether to capitalize the text in charts and figures"""
        return self.plotting.get("capitalize", False)

    @capitalize.setter
    def capitalize(self, value: bool):
        if value is not None:
            self.search_data.setdefault("plotting", dict())["capitalize"] = value

    @property
    def plotting_property_group_combinations(self) -> Optional[List[List[str]]]:
        return self.plotting.get('property_group_combinations', [])

    @property
    def libraries(self):
        return self.search_data["libraries"]

    @libraries.setter
    def libraries(self, value):
        if value is not None:
            self.search_data["libraries"] = value

    @property
    def keywords(self):
        return self.search_data["keywords"]

    @keywords.setter
    def keywords(self, value):
        if value is not None:
            self.search_data["keywords"] = value

    @property
    def properties_mandatory(self):
        if not self._properties_mandatory:
            for properties_mandatory_OR in self.search_data['properties_mandatory']:
                cur_prop = tuple(sorted(properties_mandatory_OR))
                if cur_prop not in self.properties_mandatory_internal:
                    self.properties_mandatory_internal.append(cur_prop)
            self._properties_mandatory = list()
            for properties_mandatory_OR in self.properties_mandatory_internal:
                self._properties_mandatory.append(list(properties_mandatory_OR))
            # just so that the json is consistent
            self.search_data['properties_mandatory'] = self._properties_mandatory
        return self._properties_mandatory

    @property
    def properties_excluded(self):
        return self.search_data.get('properties_excluded', {})

    @property
    def properties(self):
        return self.search_data['properties']

    @properties.setter
    def properties(self, value):
        if value is not None:
            self.search_data['properties'] = value

    @property
    def property_groups(self):
        if self._property_groups is None:
            self._property_groups = dict([(x['property_group'], x['synonyms']) for x in self.properties])
        return self._property_groups

    @property
    def property_groups_sorted(self):
        if self._property_groups_sorted is None:
            self._property_groups_sorted = sorted(self.property_groups)
        return self._property_groups_sorted

    @property
    def hd_output_property_groups(self):
        return Config.keywords_summary_header[:-2] + self.property_groups_sorted

    @property
    def start_year(self) -> int:
        return int(self.search_data.get('year_start', datetime.datetime.now().year - 10))

    @property
    def end_year(self) -> int:
        return int(self.search_data.get('year_end', datetime.datetime.now().year))

    @end_year.setter
    def end_year(self, value):
        if value is None and self.search_data.get('year_end', None) is None:
            value = datetime.datetime.now().year
        if value is not None:
            self.search_data['year_end'] = str(value)

    @start_year.setter
    def start_year(self, value):
        if self.search_data.get('year_start', None) is None and value is None:
            # 10 years, both inclusive
            value = self.end_year - 10
        if value is not None:
            self.search_data['year_start'] = str(value)

    @property
    def relevant(self) -> int:
        """Minimum number of relevant properties"""
        return int(self.search_data.get(Config.PRISMA_relevant, Config.min_properties_relevant))

    @relevant.setter
    def relevant(self, value):
        if value is not None:
            self.search_data[Config.PRISMA_relevant] = str(value)

    @property
    def folder_data(self) -> str:
        if not self._main_folder_path:
            self._main_folder_path = h.get_parent_folder(self.input_filename)
            self.search_data['path'] = self._main_folder_path
        return self._main_folder_path

    @folder_data.setter
    def folder_data(self, _folder: str):
        if _folder is None:
            _folder = h.get_parent_folder(self.input_filename)
        self._main_folder_path = _folder
        self.search_data['path'] = self._main_folder_path

    @property
    def folder_repo(self):
        return self.search_data.get("path_repo",
                                    os.path.join(os.path.dirname(os.path.realpath(self.folder_data)), 'REPO'))

    @folder_repo.setter
    def folder_repo(self, value):
        if value is not None:
            self.search_data["path_repo"] = value

    @property
    def project_id(self):
        return self.search_data.get("project_id", "-1")

    @project_id.setter
    def project_id(self, value):
        if value is not None:
            self.search_data["project_id"] = str(value)

    @property
    def project_name(self):
        return self.search_data.get("project_name", "project_name")

    @project_name.setter
    def project_name(self, value):
        if value is not None:
            self.search_data["project_name"] = str(value)

    @property
    def filename_initial(self):
        return os.path.join(self.folder_data, self._filename_json)

    @property
    def filename_bibtex_temp(self):
        return os.path.join(self.folder_data, Const.filename_bibtex_temp)

    @property
    def folder_results(self):
        return os.path.join(self.folder_data, Const.folder_results)

    @property
    def file_articles_all(self):
        return os.path.join(self.folder_results, Const.file_articles_all)

    @property
    def file_emails(self):
        return os.path.join(self.folder_results, Const.file_emails)

    @property
    def file_articles_file_articles_parsing_errors(self):
        return os.path.join(self.folder_results, Const.file_articles_parsing_errors)

    @property
    def file_articles_bib(self):
        return os.path.join(self.folder_results, Const.file_articles_bib)

    @property
    def file_articles_stemmed(self):
        return os.path.join(self.folder_results, Const.file_articles_stemmed)

    @property
    def file_results_property_groups(self):
        return os.path.join(self.folder_results, Const.file_results_property_groups)

    @property
    def file_results_properties(self):
        return os.path.join(self.folder_results, Const.file_results_properties)

    @property
    def file_results_details(self):
        return os.path.join(self.folder_results, Const.file_results_details)

    @property
    def file_results_graph_data(self):
        return os.path.join(self.folder_results, Const.file_results_graph_data)

    @property
    def file_filtered_graph_properties(self):
        # return os.path.join(self.graph_results_folder_name, 'filtered_graph_properties.csv')
        return os.path.join(self.folder_results, Const.file_filtered_graph_properties)

    @property
    def file_results_graph_plot(self):
        return os.path.join(self.folder_results, Const.file_results_graph_plot)

    @property
    def file_results_articles_filtered(self):
        return os.path.join(self.folder_results, Const.file_results_articles_filtered)

    @property
    def file_results_articles_invalid(self):
        return os.path.join(self.folder_results, Const.file_results_articles_invalid)

    @property
    def file_results_properties_filtered(self):
        return os.path.join(self.folder_results, Const.file_results_properties_filtered)

    @property
    def file_results_details_filtered(self):
        return os.path.join(self.folder_results, Const.file_results_details_filtered)

    @property
    def file_results_aggr_property_group_year(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_property_group_year)

    @property
    def file_results_aggr_property_group_year_pivot(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_property_group_year_pivot)

    @property
    def file_results_aggr_property_year(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_property_year)

    @property
    def file_results_property_group_percentage(self):
        return os.path.join(self.folder_results, Const.file_results_property_group_percentage)

    @property
    def file_results_aggr_property_year_pivot(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_property_year_pivot)

    @property
    def file_results_aggr_source_year(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_source_year)

    @property
    def file_results_aggr_year(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_year)

    @property
    def file_results_aggr_prisma(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_prisma)

    @property
    def file_results_aggr_source_year_pivot_analyzed(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_source_year_pivot_analyzed)

    @property
    def file_results_aggr_source_year_pivot_relevant(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_source_year_pivot_relevant)

    @property
    def file_results_aggr_keyword_year_pivot_relevant(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_keyword_year_pivot_relevant)

    @property
    def file_results_aggr_keyword_source_pivot_relevant(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_keyword_source_pivot_relevant)

    @property
    def file_results_aggr_source(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_source)

    @property
    def file_results_aggr_num_countries_affiliations_authors(self):
        return os.path.join(self.folder_results, Const.file_results_aggr_num_countries_affiliations_authors)

    @property
    def file_searched_keywords_final(self):
        return os.path.join(self.folder_results, Const.file_searched_keywords_final)

    @property
    def filename_log(self):
        self.create_folders()
        return os.path.join(self.folder_results, Const.filename_log)

    @property
    def filename_input_simple(self):
        self.create_folders()
        return os.path.join(self.folder_results, Const.filename_input_simple)

    @property
    def filename_status(self):
        return os.path.join(self.folder_results, Const.filename_status)

    @property
    def filename_status_long(self):
        return os.path.join(self.folder_results, Const.filename_status_long)

    @property
    def graph_results_folder_name(self):
        return os.path.join(self.folder_results, Const.graph_results_folder_name)

    @property
    def folder_ACM(self):
        return os.path.join(self.folder_repo, Config.ACM_FOLDER)

    @property
    def folder_ACM_Articles(self):
        return os.path.join(self.folder_repo, Config.ACM_FOLDER, 'articles')

    @property
    def folder_ACM_Links(self):
        return os.path.join(self.folder_repo, Config.ACM_FOLDER, 'links')

    @property
    def folder_IEEEXplore(self):
        return os.path.join(self.folder_repo, Config.IEEEXPLORE_FOLDER)

    @property
    def folder_IEEE_Articles(self):
        return os.path.join(self.folder_repo, Config.IEEEXPLORE_FOLDER, 'articles')

    @property
    def folder_IEEE_Links(self):
        return os.path.join(self.folder_repo, Config.IEEEXPLORE_FOLDER, 'links')

    @property
    def folder_Springer(self):
        return os.path.join(self.folder_repo, Config.SPRINGER_FOLDER)

    @property
    def folder_Springer_Links(self):
        return os.path.join(self.folder_repo, Config.SPRINGER_FOLDER, 'links')

    @property
    def folder_Springer_Articles(self):
        return os.path.join(self.folder_repo, Config.SPRINGER_FOLDER, 'articles')

    @property
    def folder_Springer_Data(self):
        return os.path.join(self.folder_repo, Config.SPRINGER_FOLDER, 'data')

    @property
    def folder_NCBI(self):
        return os.path.join(self.folder_repo, Config.NCBI_FOLDER)

    @property
    def folder_MDPI(self):
        return os.path.join(self.folder_repo, Config.MDPI_FOLDER)

    @property
    def folder_MDPI_links(self):
        return os.path.join(self.folder_MDPI, 'links')

    @property
    def folder_MDPI_articles(self):
        return os.path.join(self.folder_MDPI, 'articles')

    @property
    def folder_MDPI_stats(self):
        return os.path.join(self.folder_MDPI, 'stats')

    @property
    def folder_MDPI_data(self):
        return os.path.join(self.folder_MDPI, 'data')

    @property
    def folder_PubMed(self):
        return os.path.join(self.folder_repo, Config.PUBMED_FOLDER)

    @property
    def folder_PubMed_links(self):
        return os.path.join(self.folder_PubMed, 'links')

    @property
    def folder_PubMed_articles(self):
        return os.path.join(self.folder_PubMed, 'articles')

    @property
    def folder_PubMed_data(self):
        return os.path.join(self.folder_PubMed, 'data')

    @property
    def folder_Elsevier(self):
        return os.path.join(self.folder_repo, Config.ELSEVIER_FOLDER)

    @property
    def folder_Elsevier_links(self):
        return os.path.join(self.folder_Elsevier, 'links')

    @property
    def folder_Elsevier_articles(self):
        return os.path.join(self.folder_Elsevier, 'articles')

    @property
    def folder_Elsevier_Data(self):
        return os.path.join(self.folder_repo, Config.ELSEVIER_FOLDER, 'data')

    def create_folders(self):
        folders = [self.folder_data, self.folder_repo, self.folder_results, self.folder_ACM, self.folder_ACM_Articles,
                   self.folder_IEEEXplore, self.folder_IEEE_Articles, self.folder_IEEE_Links, self.folder_Springer,
                   self.folder_Springer_Links, self.folder_Springer_Articles, self.folder_NCBI, self.folder_MDPI,
                   self.folder_MDPI_links, self.folder_MDPI_articles, self.folder_MDPI_stats,
                   self.folder_PubMed, self.folder_PubMed_links,
                   self.folder_PubMed_articles, self.folder_Elsevier, self.folder_Elsevier_articles,
                   self.folder_Elsevier_links, self.folder_Elsevier_Data]
        for f in folders:
            h.create_folder(f)

    @property
    def filename_json(self):
        return os.path.join(self.folder_data, self._filename_json)

    @property
    def filename_pickle(self):
        return os.path.join(self.folder_data, self._filename_pickle)

    @filename_json.setter
    def filename_json(self, _filename_initial):
        self._filename_json = _filename_initial
        fn, exten = os.path.splitext(self._filename_json)
        self._filename_pickle = fn + '_internal.pickle'

    def set_result_counts(self, sources=None):
        if not sources:
            sources = Config.valid_sources
        if isinstance(sources, str):
            sources = [sources]
        for source in sources:
            self.result_counts.setdefault(source, {})
            for metric in Config.PRISMA_search_stats_header:
                self.result_counts[source].setdefault(metric, 0)

    def save_status(self):
        self.create_folders()
        h.to_json(self.status, self.filename_status, pretty_print=True)
        h.to_json(self.status_long, self.filename_status_long, pretty_print=True)

    def to_pickle(self):
        h.to_pickle(self, self.filename_pickle)

    def reset_folder_data(self, filename: str):
        cur_folder = h.get_parent_folder(filename)
        if self.folder_data != cur_folder:
            # in case this is a copy of a previous execution
            self.folder_data = cur_folder

    @staticmethod
    def from_pickle(filename: str) -> SearchConfig:
        d = h.from_pickle(filename)
        d.reset_folder_data(filename)
        d.create_folders()
        return d

    def save_keywords(self, input_type=None):
        if input_type is not None:
            self.keywords = ['AAL and deep learning', "ELE and machine learning"]
            self.properties = [{'property_group': 'Algorithms',
                                'synonyms': [['ANN', 'NN', 'Neural Networks'], ["DL", "Deep Learning"]]},
                               {'property_group': 'Application',
                                'synonyms': [['Activity Recognition', 'ADL'], ["Time Series Analysis"]]}]
        try:
            # json_data = h.to_json_simple(self.search_data, self.filename_json)
            self.save_object(self.filename_json)
        except Exception as e:
            h.log_line('type:', self.search_data, e)
            raise e

    @staticmethod
    def load_object(filename: str) -> SearchConfig:
        def configuration_decoder(params):
            # this is some inner dict
            return params

        with open(filename, 'r', encoding='utf-8') as fin:
            search_data = json.load(fin, object_hook=configuration_decoder)
        search = SearchConfig(filename=filename)
        search.search_data = search_data
        search.reset_folder_data(filename)
        if filename != search.filename_json:
            search.save_object()

        search.stem_properties()
        search.set_result_counts()
        return search

    def save_object(self, filename: str = None):
        if filename is None:
            filename = self.filename_json
        with open(filename, 'w', encoding='utf-8') as fout:
            json.dump(self.search_data, fout, cls=ConfigurationEncoder, indent=4)

    def _propose_synonyms_for_keywords(self):
        self.search_data['keywords'].setdefault('proposed', [])
        # dataset.search_data.setdefault('reverse_keywords',{})
        proposed = set([k.lower() for k in self.search_data['keywords']['initial']])
        for keyword in self.search_data['keywords']['initial']:
            synonyms = [s.lower() for s in tools.get_synonyms(keyword)]
            for synonym in synonyms:
                self.keyword_lookup[synonym] = keyword
            proposed.update(set(synonyms))
        self.search_data['keywords']['proposed'] = sorted(proposed)

    def _prepare_mandatory_properties(self):
        for property_excluded in self.properties_excluded:
            # add permutations as well as for the excluded
            stemmed_excluded_properties = tools.stem_text(property_excluded, self.apply_stemming)
            self.properties_excluded_stemmed.extend(tools.text_to_tuple_permutations(stemmed_excluded_properties,
                                                                      self.apply_phrase_permutations))
        self.properties_mandatory_stemmed = []
        for properties_mandatory_OR_conditions in self.properties_mandatory:
            # e.g. properties_mandatory_conditions= ['nlp', 'natural language processing'], both are synonyms, so OR
            properties_mandatory_conditions_tuples = []
            for property_mandatory in properties_mandatory_OR_conditions:
                h.log_line(property_mandatory)
                stemmed_property_mandatory = tools.stem_text(property_mandatory, self.apply_stemming)
                h.log_line(property_mandatory, stemmed_property_mandatory)
                properties_mandatory_conditions_tuples.extend(
                    tools.text_to_tuple_permutations(stemmed_property_mandatory, self.apply_phrase_permutations))
            if len(properties_mandatory_conditions_tuples) > 0:
                self.properties_mandatory_stemmed.append(list(set(properties_mandatory_conditions_tuples)))

    @property
    def properties_mandatory_internal(self):
        if self._properties_mandatory_internal is None:
            self._properties_mandatory_internal = list()
            for x in self.properties:
                current_mandatory_properties = list()
                if x.get('is_mandatory', False):
                    # this property group is mandatory, so we need to flatten all its synonyms
                    for synonyms_list in x['synonyms']:
                        current_mandatory_properties.extend(synonyms_list)
                    self._properties_mandatory_internal.append(tuple(sorted(current_mandatory_properties)))
        return self._properties_mandatory_internal

    @property
    def email_results(self):
        email_property: str = self.search_data.get("email_results", "")
        if len(email_property) == 0:
            return []
        return [email.strip() for email in email_property.split(',')]


    def _prepare_properties(self):
        self.properties_stemmed = {}
        properties_major = OrderedDict()
        for property_group, synonym_groups in self.property_groups.items():
            stemmed_synonyms = set()
            for synonyms in synonym_groups:
                if not synonyms or len(synonyms) == 0:
                    continue
                synonym_major = synonyms[0]
                properties_major[synonym_major] = None
                # This allows: wood-steel to be treated as: woodsteel, wood steel, and later on, steel wood
                synonyms_internal = synonyms + [s.replace('-', ' ') for s in synonyms if '-' in s]
                for synonym in synonyms_internal:
                    stemmed_synonym = tools.stem_text(synonym, self.apply_stemming)
                    stemmed_synonym_tuples = tools.text_to_tuple_permutations(stemmed_synonym,
                                                                              self.apply_phrase_permutations)
                    for stemmed_synonym_tuple in stemmed_synonym_tuples:
                        self.property_stem_lookup_tuple.setdefault(stemmed_synonym_tuple, set())
                        self.property_stem_lookup_tuple[stemmed_synonym_tuple].add(property_group)
                        self.stem_source_lookup_tuple[stemmed_synonym_tuple] = synonym
                    self.property_lookup.setdefault(synonym, set())
                    self.property_lookup[synonym].add(property_group)
                    self.property_stem_lookup.setdefault(stemmed_synonym, set())
                    self.property_stem_lookup[stemmed_synonym].add(property_group)

                    self.property_synonym_lookup.setdefault(synonym, set())
                    self.property_synonym_lookup[synonym].add(synonym_major)
                    self.stem_source_lookup[stemmed_synonym] = synonym
                    stemmed_synonyms.add(stemmed_synonym)
            self.properties_stemmed[property_group] = sorted(stemmed_synonyms)
        self.properties_major = list(properties_major.keys())

    def stem_properties(self):
        self.set_status("Property Stemming", "Starting")
        self._prepare_properties()
        self._prepare_mandatory_properties()
        self.set_status("Property Stemming")
        self.to_pickle()

    def write_results(self, data, filename):
        # with self.lock:
        self.result_files.add(filename)
        if data is None:
            data = []
        if len(data) > 0 and data[0] != Config.keywords_result_header:
            data = [Config.keywords_result_header] + data
        if len(data) > 0:
            headers = data[0]
            data = data[1:]
        else:
            headers = Config.keywords_result_header
        df = pd.DataFrame(data=data, columns=headers)
        hio.df_to_csv(df, filename, write_to_excel_too=True)
        self.to_pickle()

    def set_parameters(self, ieee: bool = None, pmc: bool = None, pubmed: bool = None, springer: bool = None,
                       elsevier: bool = None, mdpi: bool = None, acm: bool = None, folder_repo: str = None,
                       relevant: int = None, add_lin_coef: bool = None, plot_type: str = None, capitalize: bool = None,
                       stem: bool = None, start_year: int = None, end_year: int = None,  multithread: bool = None,
                       delete_cache: bool = None):
        self.project_id = -1
        self.project_name = None
        self.folder_repo = folder_repo
        self.relevant = relevant
        self.add_lin_coef = add_lin_coef
        self.apply_stemming = stem
        self.plot_type = plot_type
        self.capitalize = capitalize
        self.end_year = end_year
        self.start_year = start_year
        self.set_library_enabled("ieee", ieee)
        self.set_library_enabled("pmc", pmc)
        self.set_library_enabled("pubmed", pubmed)
        self.set_library_enabled("springer", springer)
        self.set_library_enabled("acm", acm)
        self.set_library_enabled("elsevier", elsevier)
        self.set_library_enabled("mdpi", mdpi)
        self.multithread = multithread
        self.delete_cache = delete_cache
        self.create_folders()
        h.setup_logging(output_filename=self.filename_log)

    @staticmethod
    def prepare_search_object(filename: str, ieee: bool = None, pmc: bool = None, pubmed: bool = None,
                              springer: bool = None, acm: bool = None, folder_repo: str = None, relevant: int = None,
                              add_lin_coef: bool = False, plot_type: str = 'pdf', capitalize: bool = False,
                              stem: bool = True, start_year: int = None, end_year: str = None, folder: str = None,
                              multithread: bool = True, delete_cache: bool = False) -> SearchConfig:
        if filename.lower().endswith('pkl') or filename.lower().endswith('pickle'):
            search = SearchConfig.from_pickle(filename)
        elif filename.lower().endswith('json'):
            search = SearchConfig.load_object(filename)
        else:
            raise Exception("Filetype not supported:" + filename)
        search.set_parameters(ieee=ieee, pmc=pmc, pubmed=pubmed, springer=springer, acm=acm,
                              folder_repo=folder_repo, relevant=relevant, add_lin_coef=add_lin_coef,
                              plot_type=plot_type, capitalize=capitalize, stem=stem,
                              start_year=start_year, end_year=end_year, multithread=multithread,
                              delete_cache=delete_cache)
        return search


class ConfigurationEncoder(json.JSONEncoder):
    def default(self, obj):
        config_params = dict()
        config_params['__type__'] = obj.__class__.__name__
        config_params.update(obj.__dict__)
        return config_params
