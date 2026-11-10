# import csv
import os
import random
import threading
import time
from math import ceil
from threading import Lock
from typing import Tuple, Optional, Any
from urllib.parse import quote

import pandas as pd
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError, Error
from slugify import slugify

from configuration.config import *
from core.search_config import SearchConfig
from help_tools import helpers as h, hio
from help_tools.browser_emulate import create_playwright_browser, PlaywrightBrowser
from help_tools.tools import tools

c_int = tools.ignore_exception(ValueError)(int)


class IEEEXplore(object):
    ROWS_PER_PAGE = 100
    # CONSTANTS
    ABSOLUTE_URI = 'https://ieeexplore.ieee.org'
    URL_2021 = ABSOLUTE_URI + '/search/searchresult.jsp?queryText={keyword}&highlight=true&returnFacets=ALL&' \
                              'returnType=SEARCH&matchPubs=true&pageNumber={page_number}&ranges={year_from}_{year_to}_Year&returnFacets=ALL&rowsPerPage='+str(ROWS_PER_PAGE)
    # url_template = 'http://ieeexplore.ieee.org/search/searchExport.jsp?queryText={0}&ranges={1}_{2}_Year'
    # url_template_2020 = 'https://ieeexplore.ieee.org/search/searchresult.jsp?' \
    #                     'queryText={0}&highlight=true&returnFacets=ALL&returnType=SEARCH&ranges={1}_{2}_Year'
    random_delay_min = 2
    random_delay_max = 6
    max_attempts = 3
    backoff_factor = 2

    @staticmethod
    def crawl(search: SearchConfig, lock: Lock = threading.Lock(), keyword: str = None, force_crawl: bool = False):
        """
        The public method to call for crawling the IEEE Xplore database by the search configuration provided.

        :param search: An object that contains all information about the crawling
        :type search: SearchConfig
        :param lock: A Lock object used for protection of search object
        :type lock: Lock
        :param keyword: A keyword for crawling (Optional parameter)
        :type keyword: str
        :param force_crawl: If True, the method will crawl again for each keyword even if some old results already exist
        :type force_crawl: bool
        """

        with sync_playwright() as p:
            pw = create_playwright_browser(playwright=p)
            try:
                with lock:
                    search.set_status(key='IEEE', value='Starting')
                    h.log_line('Starting crawling for IEEE Xplore.')
                    search.set_result_counts(sources=Config.sources.get('ieee', 'IEEE Xplore'))

                # Iterate through all keywords and process them one-by-one by getting all the articles and scraping each of them
                if keyword is not None:
                    IEEEXplore._process_keyword(search, keyword, lock, pw, search.force_crawl)
                else:
                    for keyword in search.keywords:
                        IEEEXplore._process_keyword(search, keyword, lock, pw, search.force_crawl)

                    # write into status and log files
                with lock:
                    search.set_status(key='IEEE', value='Completed')
                    h.log_line('Finished crawling for IEEE Xplore.')
                    search.to_pickle()
            finally:
                pw.context.close()
                pw.browser.close()

    @staticmethod
    def _process_keyword(search: SearchConfig, keyword: str, lock: Lock, pw: PlaywrightBrowser, force_crawl: bool = False) -> None:
        """
        Process the IEEE database for a certain keyword (crawl + scrape articles)

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
        h.log_line(f'Starting to process keyword {keyword} for IEEE database.')
        # browser, context, page = create_playwright_browser()

        article_links, links_filename = IEEEXplore._crawl_keyword(search, keyword, force_crawl, pw)

        if (isinstance(article_links, pd.DataFrame) and article_links.empty) or (isinstance(article_links, set) and len(article_links) > 0):
            articles_data = IEEEXplore._scrape_articles(search, article_links, keyword, lock, pw)
            with lock:
                search.write_results(articles_data, links_filename)

        # write into log files
        h.log_line(f'Finished processing keyword {keyword} for IEEE database.')

    @staticmethod
    def _crawl_keyword(search: SearchConfig, keyword: str, force_crawl: bool, pw: PlaywrightBrowser) -> Tuple[Optional[pd.DataFrame], str]:
        """
       Crawl the IEEE database for a certain keyword and download a CSV file with list of articles.

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
        keyword_folder = os.path.join(search.folder_IEEE_Links, keyword_slug)
        h.create_folder(keyword_folder)
        # keyword_urls_filename = os.path.join(keyword_folder, keyword_slug + '_urls.csv')
        keyword_links_filename = os.path.join(keyword_folder, keyword_slug + '_links.csv')

        # return the crawled dataframe instead
        if os.path.isfile(keyword_links_filename) and os.stat(keyword_links_filename).st_size > 0 and force_crawl is False:
            h.log_line('File exists: ', keyword_links_filename)
            h.log_line('Skipping IEEE download of ', keyword)
            h.log_line('Reading from file: ', keyword_links_filename)
            scraped_articles = hio.pd_read_csv_or_excel(filename=keyword_links_filename, sep='\t', encoding='UTF-8')

            return scraped_articles, keyword_links_filename
        # if os.path.isfile(keyword_urls_filename) and os.stat(keyword_urls_filename).st_size > 0 \
        #         and force_crawl is False:
        #     h.log_line('File exists: ', keyword_urls_filename)
        #     h.log_line('Skipping IEEE download of ', keyword)
        #     h.log_line('Reading from file: ', keyword_urls_filename)
        #     urls_data = hio.pd_read_csv_or_string_stream(filename=keyword_urls_filename, sep=',', encoding='UTF-8')
        #
        #     return urls_data, keyword_links_filename

        # Create the download URL
        url_keyword = quote(keyword)
        year_from = search.start_year
        year_to = search.end_year
        result_page_links = set()

        page_count_css_selector = '#xplMainContent > div.ng-Dashboard > div.col > xpl-search-dashboard > section > div > h1 > span:nth-child(1) > span:nth-child(2)'

        # try to fetch page count from page, or else default to constant
        try:
            download_url = IEEEXplore.URL_2021.format(year_from=year_from, year_to=year_to, keyword=url_keyword,
                                                      page_number=1)
            # Use exponential backoff for requests
            if IEEEXplore.request_with_backoff(pw, download_url, timeout=Config.browser_delay_time_ieee * 1000):
                page_count_text = pw.page.locator(page_count_css_selector).nth(0).text_content()
                if page_count_text is None:
                    page_count_text = ''
                page_count = ceil(int(page_count_text.replace(',', '').strip()) / IEEEXplore.ROWS_PER_PAGE)
                h.log_line('Page count:', page_count)
            else:
                h.log_line("Failed to fetch page count from IEEE. Using default page count instead.")
                page_count = Config.number_of_pages_ieee
        except TimeoutError as ex:
            h.log_line(ex)
            page_count = Config.number_of_pages_ieee

        page_count = min(page_count, Config.number_of_pages_ieee)  # in case page number is more than constant

        for i in range(1, page_count + 1):
            if i > 0 and i % 10 == 0:
                pw.rotate_context()
            try:
                download_url = IEEEXplore.URL_2021.format(year_from=year_from, year_to=year_to, keyword=url_keyword, page_number=i)
                # pw.page.goto(download_url, wait_until="domcontentloaded")
                IEEEXplore.request_with_backoff(pw, download_url, timeout=Config.browser_delay_time_ieee * 1000, wait_for_element='.List-results-items')

                link_elems_on_page = pw.page.locator("css=.List-results-items div h3 a").all()
                links_on_page = [link.get_attribute("href") for link in link_elems_on_page]

                if len(links_on_page) > 0:
                    result_page_links.update(links_on_page)
                else:
                    h.log_line('Breaking at page:', i, 'because no new links were found. Total links:', len(links_on_page))
                    break
            except Error as e:
                h.log_line(f"IEEE search error. Exception: {e}")

        return result_page_links, keyword_links_filename

    @staticmethod
    def _scrape_articles(search: SearchConfig, article_links, keyword: str, lock: Lock, pw: PlaywrightBrowser):

        # write to log files
        h.log_line(f'Starting to process articles found for keyword: {keyword} for IEEE database.')

        IEEE_source = Config.sources.get('ieee', 'IEEE Xplore')
        articles_data = []
        # iter tuples has problems with columns with space in the name
        # articles.columns = articles.columns.str.replace(r'\s+', '_', regex=True)
        # articles.fillna(value='', inplace=True)

        for i, link in enumerate(article_links):
            if i > 0 and i % 10 == 0:
                pw.rotate_context()

            valid_doi, date = "", ""
            year = 0

            # introduce random delays to reduce throttling and detection
            time.sleep(random.uniform(1.5, 4.0))
            try:
                IEEEXplore.request_with_backoff(pw, IEEEXplore.ABSOLUTE_URI+link, timeout=Config.browser_delay_time_ieee * 1000)
                # pw.page.goto(IEEEXplore.ABSOLUTE_URI+link, wait_until="domcontentloaded")
            except Error as e:
                h.log_line(f"IEEE page load timed out. Error: {e}")
                continue
            title = ""
            try:
                title_h1 = pw.page.locator('css=.document-title')
                title = title_h1.text_content()
            except TimeoutError:
                continue
            try:
                number_of_citations_div = pw.page.locator('css=.document-banner-metric-count').nth(0)
                number_of_citations = int(number_of_citations_div.text_content())
            except TimeoutError:
                number_of_citations = 0
            try:
                abstract_div = pw.page.locator('css=.abstract-text')
                abstract = abstract_div.text_content()
            except TimeoutError:
                abstract = ""

            final_url = link
            try:
                publication_title_div = pw.page.locator('css=.stats-document-abstract-publishedIn').nth(0)
                publication_title = publication_title_div.text_content()
            except TimeoutError:
                publication_title = ""
            try:
                doi_a = pw.page.locator('css=.stats-document-abstract-doi a').nth(0)
                valid_doi = doi_a.text_content()
            except TimeoutError:
                valid_doi = ""

            # date_div_class_names = ['doc-abstract-pubdate', 'doc-abstract-confdate', 'doc-abstract-dateadded']
            date_text = ""
            try:
                date_div = pw.page.locator('css=.doc-abstract-pubdate, .doc-abstract-confdate, .doc-abstract-dateadded').nth(0)
                date_text = date_div.text_content()
            except TimeoutError:
                continue

            # for class_name in date_div_class_names:
            #     try:
            #         date_div = page.locator(f'css=.{class_name}')
            #         date_text = date_div.text_content()
            #     except TimeoutError:
            #         continue
            if date_text != "":
                date_list = date_text.strip().split(" ")
                date = ' '.join(date_list[-3:])
                year = None
                if date_list is not None and date_list[-1] != '':
                    year = int(date_list[-1])

            authors_button_xpath = '//*[@id="document-tabs"]/div[2]/a'
            # authors_button.click()
            try:
                pw.page.locator(f'xpath={authors_button_xpath}').click()
                authors_divs = pw.page.locator('css=.authors-accordion-container').all()

                # author_name_xpaths = ['//*[@id="authors"]/div[1]/xpl-author-item/div/div[1]/div/div[1]/a/span',
                # '//*[@id="authors"]/div[1]/xpl-author-item/div/div[1]/div/div/xpl-modal/a/span']
                # author_affiliation_xpath = '//*[@id="authors"]/div[1]/xpl-author-item/div/div[1]/div/div[2]/div'


                authors_list = []
                affiliations_list = set()
                countries_list = set()

                author_name_divs = pw.page.locator("css=#authors xpl-author-item a span").all()
                author_names = [name.text_content() for name in author_name_divs]


                affiliation_divs = pw.page.locator("css=#authors xpl-author-item div div div:nth-child(2) div").all()
                affiliations = [affiliation.text_content() for affiliation in affiliation_divs]

                countries = [affiliation.split(",")[-1].strip() for affiliation in affiliations]

                if countries is not None and len(countries) > 0:
                    countries_list = set(countries)

                if affiliations is not None and len(affiliations) > 0:
                    affiliations_list = set(affiliations)

                if author_names is not None and len(author_names) > 0:
                    authors_list = author_names

            except TimeoutError:
                authors_list = []
                affiliations_list = []
                countries_list = []

            authors = ", ".join(authors_list)
            affiliations = ", ".join(affiliations_list)
            countries = ", ".join(countries_list)

            number_different_affiliations = len(affiliations_list)
            number_different_countries = len(countries_list)
            number_of_authors = len(authors_list)

            emails = ""
            fields = (valid_doi, final_url, title, authors, date, year, number_of_citations, abstract,
                      keyword, IEEE_source, publication_title, affiliations, number_different_affiliations,
                      countries, number_different_countries, number_of_authors, emails)

            # Do not process the article if there is no information about the title, the authors or the abstract
            if h.is_empty(title) or h.is_empty(authors) or len(abstract) <= Config.abstract_min_length:
                with lock:
                    search.result_counts[IEEE_source][Config.PRISMA_parsing_errors] += 1
                    search.parsing_errors_articles.append(fields)

                h.log_line(f'Skipping to process article for url: {final_url} because the data is incomplete.')
                continue
            if h.is_empty(valid_doi):
                # This is a case when everything else was parsed successfully, but somehow the DOI wasn't correct,
                # which is not a critical issue
                with lock:
                    search.parsing_errors_articles.append(fields)
            articles_data.append(list(fields))

            if len(articles_data) >= Config.max_papers_ieee:
                h.log_line('Breaking scraping articles for', IEEE_source, 'because max papers:',
                           Config.max_papers_ieee, 'was reached.', 'Total scraped articles:', len(articles_data))
                break

        h.log_line('Finished with processing articles found for keyword:', keyword,
                   'for IEEE database.')
        return articles_data

    @staticmethod
    def request_with_backoff(pw: PlaywrightBrowser, url: str, attempt: int = 1, wait_until: str = 'domcontentloaded', timeout: int = None):
        """
        Make a request with exponential backoff strategy to handle rate limiting

        :param page: The Playwright page object
        :param url: The URL to navigate to
        :param attempt: Current attempt number (starts at 1)
        :param wait_until: Navigation wait criteria
        :param timeout: Navigation timeout in milliseconds
        :return: True if successful, False if all attempts failed
        """
        try:
            # # Calculate delay with exponential backoff
            # base_delay = random.uniform(IEEEXplore.random_delay_min, IEEEXplore.random_delay_max)
            # delay = base_delay * (IEEEXplore.backoff_factor ** (attempt - 1))
            #
            # h.log_line(f"Request attempt {attempt} for {url}. Waiting {delay:.2f} seconds...")
            # # time.sleep(delay)

            # If timeout is not provided, use the config default
            if timeout is None:
                timeout = Config.browser_delay_time_elsevier * 1000

            res = pw.page.goto(url, wait_until=wait_until, timeout=timeout)
            if res.status != 200:
                raise Exception(f"Request failed with status code {res.status}")
            return True

        except Exception as e:
            h.log_line("Rotating context because of rate limit")
            pw.rotate_context()
            if attempt < IEEEXplore.max_attempts:
                h.log_line(f"Retrying... (Attempt {attempt + 1} of {IEEEXplore.max_attempts})")
                return IEEEXplore.request_with_backoff(pw, url, attempt + 1, wait_until, timeout)
            else:
                h.log_line(f"Max attempts ({IEEEXplore.max_attempts}) reached. Giving up on: {url}")
                return False
