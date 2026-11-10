import json
import os
import re
import threading
from threading import Lock
from urllib.parse import quote_plus

import pandas as pd
from typing import Tuple, Optional, List

from slugify import slugify

from help_tools import helpers as h, hio
from help_tools.browser_emulate import download_links
from configuration.config import *
from help_tools.countries import Countries
from core.search_config import SearchConfig
from help_tools.helpers import is_email_valid
from help_tools.tools import tools


class PubMed:

    # CONSTANTS
    ABSOLUTE_URI = 'https://pubmed.ncbi.nlm.nih.gov'
    URL_TEMPLATE = ABSOLUTE_URI + '/?term={keyword}&filter=years.{year_from}-{year_to}'

    @staticmethod
    def crawl(search: SearchConfig, lock: Lock = threading.Lock(), keyword: str = None, force_crawl: bool = False):
        """
        The public method to call for crawling the NCBI PubMed database by the search configuration provided.

        :param search: An object that contains all information about the crawling
        :type search: SearchConfig
        :param lock: A Lock object used for protection of search object
        :type lock: Lock
        :param keyword: A keyword for crawling (Optional parameter)
        :type keyword: str
        :param force_crawl: If True, the method will crawl again for each keyword even if some old results already exist
        :type force_crawl: bool
        """

        with lock:
            # write into status and log files and set default for result counts
            search.set_status(key='PubMed', value='Starting')
            h.log_line('Starting crawling for NCBI:PubMed.')
            search.set_result_counts(sources=Config.sources.get('pubmed', 'NCBI:PubMed'))

        # Iterate through all keywords and process them one-by-one by getting all the articles and scraping each of them
        if keyword is not None:
            PubMed._process_keyword(search, keyword, lock, search.force_crawl)
        else:
            for keyword in search.keywords:
                PubMed._process_keyword(search, keyword, lock, search.force_crawl)
        with lock:
            search.set_status(key='PubMed', value='Completed')
            h.log_line('Finished crawling for NCBI:PubMed.')
            search.to_pickle()

    @staticmethod
    def _process_keyword(search: SearchConfig, keyword: str, lock: Lock, force_crawl: bool = False):
        """
        Process the NCBI PubMed database for a certain keyword (crawl + scrape articles)

        :param search: An object that contains all information about the crawling
        :type search: SearchConfig
        :param keyword: The keyword used for crawling
        :type keyword: str
        :param lock: A Lock object used for protection of search object
        :type lock: Lock
        :param force_crawl: If True, the method will crawl again for each keyword even if some old results already exist
        :type force_crawl: bool
        """

        # write into log files
        h.log_line(f'Starting to process keyword {keyword} for NCBI:PubMed database.')

        articles, links_filename = PubMed._crawl_keyword(search, keyword, force_crawl)

        if articles is not None:
            articles_data = PubMed._scrape_articles(search, articles, keyword, lock)
            with lock:
                search.write_results(articles_data, links_filename)

        # write into log files
        h.log_line(f'Finished processing keyword {keyword} for NCBI:PubMed database.')

    @staticmethod
    def _crawl_keyword(search: SearchConfig, keyword: str, force_crawl: bool) -> Tuple[Optional[pd.DataFrame], str]:
        """
       Crawl the NCBI PubMed database for a certain keyword and download a CSV file with list of articles.

       :param search: An object that contains all information about the crawling
       :type search: SearchConfig
       :param keyword: The keyword used for crawling
       :type keyword: str
       :param force_crawl: If True, the method will crawl again for each keyword even if some old results already exist
       :type force_crawl: bool

       :return: Dataset with links and other information about found articles
       :rtype: pd.DataFrame
       """

        # define folder and file names and create folders
        keyword_slug = slugify(keyword)
        keyword_folder = os.path.join(search.folder_PubMed_links, keyword_slug)
        h.create_folder(keyword_folder)
        h.create_folder(search.folder_PubMed_data)
        keyword_urls_filename = os.path.join(keyword_folder, keyword_slug + '_urls.csv')
        keyword_links_filename = os.path.join(keyword_folder, keyword_slug + '_links.csv')

        # Return previously crawled results if force crawl is negative
        if os.path.isfile(keyword_urls_filename) and os.stat(keyword_urls_filename).st_size > 0 \
                and search.force_crawl is False:
            h.log_line('File exists: ', keyword_urls_filename)
            h.log_line('Skipping NCBI:PubMed download of ', keyword)
            h.log_line('Reading from file: ', keyword_urls_filename)
            urls_data = hio.pd_read_csv_or_string_stream(filename=keyword_urls_filename, sep=',', encoding='UTF-8')

            return urls_data, keyword_links_filename

        # Create the download URL
        url_keyword = quote_plus(keyword)
        year_from = search.start_year
        year_to = search.end_year
        download_url = PubMed.URL_TEMPLATE.format(year_from=year_from, year_to=year_to, keyword=url_keyword)

        # Download file
        status = download_links(url=download_url, exported_file_name=keyword_urls_filename, source='pubmed')
        if status:  # The download was successful
            urls_data = hio.pd_read_csv_or_string_stream(filename=keyword_urls_filename, sep=',', encoding='UTF-8')
            return urls_data, keyword_links_filename
        else:  # The download was not successful
            return None, keyword_links_filename

    ABSTRACT_XPATHS = ['//*[@id="enc-abstract"]/p/text()',
                       '//*[@id="eng-abstract"]/p/text()']

    AFFILIATIONS_XPATHS = ['//*[@id="full-view-expanded-authors"]//div[contains(@class, "affiliations")]/ul/li/text()',
                           '//*[@id="full-view-expanded-authors"]/div/ul/li/text()']

    CITATIONS_XPATHS = ['//*[@id="citedby"]/h2/em[contains(@class, "amount")]/text()',
                        '//*[@id="citedby"]/h2/em[1]/text()']

    PUBLICATION_TITLE_XPATHS = ['//*[@id="full-view-journal-trigger"]/@title']

    @staticmethod
    def _scrape_articles(search: SearchConfig, articles: pd.DataFrame, keyword: str, lock):

        # write to log files
        h.log_line(f'Starting to process articles found for keyword: {keyword} for NCBI:PubMed database.')

        PubMed_source = Config.sources.get('pubmed', 'NCBI:PubMed')
        articles_data = []
        # iter tuples has problems with columns with space in the name
        articles.columns = articles.columns.str.replace(r'\s+', '_', regex=True).str.replace('/', '_')
        articles.fillna(value='', inplace=True)

        for article in articles.itertuples(index=False):

            # extract title
            title = getattr(article, 'Title', '')
            article_id = getattr(article, 'PMID', '')  # The article ID is part of the URL for the article page
            final_url = f"{PubMed.ABSOLUTE_URI}/{article_id}/"
            if h.is_empty(article_id):
                with lock:
                    search.result_counts[PubMed_source][Config.PRISMA_parsing_errors] += 1
                h.log_line('Skipping to process article for url:', final_url,
                           'because there is no specific page for the article (incomplete data).')
                continue
            # extract DOI
            doi = getattr(article, 'DOI', None)
            valid_doi = tools.extract_doi(doi)
            if h.is_empty(doi):
                _doi = tools.simplify_url(final_url)
                if len(_doi) > 0:
                    valid_doi = _doi
                else:
                    valid_doi = h.remove_nonalpha(title, '')

            # extract authors, date, year
            authors = getattr(article, 'Authors', '')
            number_of_authors = len(authors.split(','))
            date = getattr(article, 'Create_Date', None)
            try:
                year = int(getattr(article, 'Publication_Year', -1))
            except ValueError as ve:
                h.log_line(ve)
                year = -1

            # extract publication title in abbreviated form
            short_publication_title = getattr(article, 'Journal_Book', '')

            # Scrape the article page for publication title, abstract, affiliations and number of citations
            article_filename = tools.html_filename(final_url, search.folder_PubMed_articles)
            data_filename = tools.json_filename(final_url, search.folder_PubMed_data)

            if search.delete_cache and os.path.isfile(data_filename):
                os.remove(data_filename)

            if os.path.isfile(data_filename) and os.stat(data_filename).st_size > 0:
                h.log_line('File exists:', data_filename, 'Skipping download of', final_url)

                with open(data_filename, 'r') as fin:
                    data = json.load(fin)

                publication_title = data['publication_title']
                abstract = data['abstract']
                number_of_citations = data['number_of_citations']
                emails = data['emails']
                affiliations = data['affiliations']
                number_different_affiliations = data['number_of_affiliations']
                countries = data['countries']
                number_different_countries = data['number_of_countries']

                h.log_line(f'Pubmed data caching for article {final_url}')

            else:
                publication_title = abstract = number_of_citations = emails = None
                affiliations = number_different_affiliations = countries = number_different_countries = None
                try:
                    web_page, final_url = tools.download_page(final_url, article_filename)

                    # extract abstract from the article
                    abstract = PubMed.find_xpath_in_html(web_page, PubMed.ABSTRACT_XPATHS)
                    abstract = tools.clean_and_strip_string(abstract)

                    # extract the affiliations and emails
                    email_regex = '[\w\.-]+@[\w\.-]+\.\w+'
                    email_pattern = re.compile(email_regex)

                    affiliations_crawl = PubMed.find_xpath_in_html(web_page, PubMed.AFFILIATIONS_XPATHS)
                    affiliations = []
                    emails = ''

                    if h.is_empty(affiliations_crawl):
                        (affiliations, number_different_affiliations,
                         countries, number_different_countries) = '', 0, '', 0
                    else:
                        emails = []
                        for affiliation in affiliations_crawl:
                            affiliation = str(affiliation)  # convert to string object
                            affiliation_emails = email_pattern.findall(affiliation)  # find all emails if they exist
                            if len(affiliation_emails) > 0:  # if the emails exist
                                emails.extend(affiliation_emails)
                                # iterate through each email and extract from affiliation
                                for email in affiliation_emails:
                                    affiliation = affiliation.replace(email, '')
                            affiliations.append(affiliation)

                        emails = ';'.join([email for email in emails if is_email_valid(email)])
                        affiliations = ';'.join(affiliations)
                        (affiliations, number_different_affiliations,
                         countries, number_different_countries) = Countries.process_affiliations(affiliations)

                    # There may be wrong calculation because of irregular affiliation writing
                    if number_different_countries > number_of_authors:
                        number_different_countries = number_of_authors

                    # extract number of citations
                    number_of_citations = PubMed.find_xpath_in_html(web_page, PubMed.CITATIONS_XPATHS)
                    number_of_citations = tools.clean_and_strip_string(number_of_citations)
                    if h.is_empty(number_of_citations):
                        number_of_citations = 0

                    # extract full name for publication title
                    full_publication_title = PubMed.find_xpath_in_html(web_page, PubMed.PUBLICATION_TITLE_XPATHS)
                    publication_title = tools.clean_and_strip_string(full_publication_title)
                    if h.is_empty(publication_title):
                        publication_title = short_publication_title

                except Exception as ex:
                    h.log_line('Error while trying to scrape the article page:', final_url, ex)
                    continue
                finally:
                    data = {
                            "publication_title": publication_title,
                            "abstract": abstract,
                            "number_of_citations": number_of_citations,
                            "emails": emails,
                            "affiliations": affiliations,
                            "number_of_affiliations": number_different_affiliations,
                            "countries": countries,
                            "number_of_countries": number_different_countries
                    }
                    data = json.dumps(data)
                    with open(data_filename, 'w', encoding='UTF-8') as fj:
                        fj.write(data)

            fields = (valid_doi, final_url, title, authors, date, year, number_of_citations, abstract,
                      keyword, PubMed_source, publication_title, affiliations, number_different_affiliations,
                      countries, number_different_countries, number_of_authors, emails)

            # Do not process the article if there is no information about the title, the authors or the abstract
            if h.is_empty(title) or h.is_empty(authors) or h.is_empty(abstract)\
                    or len(abstract) <= Config.abstract_min_length:
                with lock:
                    search.result_counts[PubMed_source][Config.PRISMA_parsing_errors] += 1
                    search.parsing_errors_articles.append(fields)
                h.log_line('Skipping to process article for url:', final_url, 'because the data is incomplete.')
                continue
            if h.is_empty(valid_doi):
                # This is a case when everything else was parsed successfully, but somehow the DOI wasn't correct,
                # which is not a critical issue
                with lock:
                    search.parsing_errors_articles.append(fields)

            articles_data.append(fields)

            if len(articles_data) >= Config.max_papers_pubmed:
                h.log_line('Breaking scraping articles for', PubMed_source, 'because max papers:',
                           Config.max_papers_pubmed, 'was reached.', 'Total scraped articles:', len(articles_data))
                break

        h.log_line('Finished with processing articles found for keyword:', keyword,
                   'for NCBI:PubMed database.')

        return articles_data

    @staticmethod
    def find_xpath_in_html(html_text, xpaths: List[str]):
        """
        Iterate through multiple xpaths to search in HTML text

        :param html_text: The HTML text
        :type html_text: HTMLElement
        :param xpaths: Multiple xpaths
        :type xpaths: List[str]

        :return: The found element (None if it is not found)
        """

        for xpath in xpaths:
            element = html_text.xpath(xpath)
            if element:
                return element
