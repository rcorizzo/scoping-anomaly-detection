import json
import os
import random
import threading
import time
from threading import Lock
from typing import Tuple, List, Optional, Any
from urllib.parse import quote

import pandas as pd
from lxml import etree, html
from playwright.sync_api import Page, sync_playwright, Error, TimeoutError
from slugify import slugify

import help_tools.helpers as h
from configuration.config import *
from core.search_config import SearchConfig
from help_tools import hio
from help_tools.browser_emulate import download_page_elsevier, create_playwright_browser, PlaywrightBrowser
from help_tools.countries import Countries
from help_tools.tools import tools


class Elsevier:

    # CONSTANTS
    PAGE_COUNT = 100  # How many articles to show on a page
    ABSOLUTE_URI = 'https://www.sciencedirect.com'
    URL_TEMPLATE = ABSOLUTE_URI + '/search?qs={keyword}&date={year_from}-{year_to}&show={page_count}&offset={offset}'
    random_delay_min = 2
    random_delay_max = 6
    max_attempts = 3
    backoff_factor = 2

    @staticmethod
    def crawl(search: SearchConfig, lock: Lock = threading.Lock(), keyword: str = None, force_crawl: bool = False):
        """
        The public method to call for crawling the Elsevier database by the search configuration provided.

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
                    # write into status and log files and set default for result counts
                    search.set_status(key='Elsevier', value='Starting')
                    h.log_line('Starting crawling for Elsevier.')
                    search.set_result_counts(sources=Config.sources.get('elsevier', 'Elsevier'))

                # Iterate through all keywords and process them one-by-one by getting all the articles and scraping each of them
                if keyword is not None:
                    Elsevier._process_keyword(search, keyword, lock, search.force_crawl, pw)
                else:
                    for keyword in search.keywords:
                        Elsevier._process_keyword(search, keyword, lock, search.force_crawl,pw)

                with lock:
                    search.set_status(key='Elsevier', value='Completed')
                    h.log_line('Finished crawling for Elsevier.')
                    search.to_pickle()
            finally:
                pw.context.close()
                pw.browser.close()

    @staticmethod
    def _process_keyword(search: SearchConfig, keyword: str, lock: Lock, force_crawl: bool, pw: PlaywrightBrowser):
        """
        Process the Elsevier database for a certain keyword and store all results in a file.

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
        h.log_line(f'Starting to process keyword {keyword} for Elsevier database.')
        links, links_filename = Elsevier._crawl_keyword(search, keyword, force_crawl, pw)

        # scrape pages here
        articles_data = []
        for link, article_html in links:
            article_data = Elsevier._scrape_article_page(search, link, keyword, article_html, pw, lock)

            if article_data:
                articles_data.append(article_data)
                if len(articles_data) >= Config.max_papers_elsevier:
                    h.log_line('Breaking scraping articles for', Config.sources['elsevier'], 'because max papers:',
                               Config.max_papers_elsevier, 'was reached.', 'Total scraped articles:',
                               len(articles_data))
                    break
        with lock:
            search.write_results(articles_data, links_filename)

        # write into log files
        h.log_line(f'Finished processing keyword {keyword} for Elsevier database.')

    @staticmethod
    def _crawl_keyword(search: SearchConfig, keyword: str, force_crawl: bool, pw: PlaywrightBrowser) -> Tuple[List[List[str]], str]:
        """
        Crawl the Elsevier database for a certain keyword and store all results in a file.

        :param search: An object that contains all information about the crawling
        :type search: SearchConfig
        :param keyword: The keyword used for crawling
        :type keyword: str
        :param force_crawl: If True, the method will crawl again for each keyword even if some old results already exist
        :type force_crawl: bool

        :return: All links for the articles found for the keyword and the filename where the link results will be stored
        :rtype: Tuple[List[List[str]], str]
        """
        # define folder and file names and create folders
        keyword_slug = slugify(keyword)
        keyword_folder = os.path.join(search.folder_Elsevier_links, keyword_slug)
        h.create_folder(keyword_folder)
        h.create_folder(search.folder_Elsevier_Data)
        keyword_urls_filename = os.path.join(keyword_folder, keyword_slug + '_urls_only.csv')
        keyword_page_template = os.path.join(keyword_folder, keyword_slug + '_page-{page}.txt')
        keyword_links_filename = os.path.join(keyword_folder, keyword_slug + '_links.csv')
        # Return previously crawled results if force crawl is negative
        if os.path.isfile(keyword_urls_filename) and os.stat(keyword_urls_filename).st_size > 0 \
                and search.force_crawl is False:
            h.log_line('File exists: ', keyword_urls_filename)
            h.log_line('Skipping Elsevier download of ', keyword)
            h.log_line('Reading from file: ', keyword_urls_filename)
            links_df = hio.pd_read_csv_or_string_stream(filename=keyword_urls_filename, encoding='UTF-8')
            links = links_df[['link', 'link_data']].values.tolist()
            links = [[link, link_data[2:-1]] for link, link_data in links]  # remove characters to be read properly

            return links, keyword_links_filename


        links = []
        links_unique = set()
        url_keyword = quote(keyword)
        year_from = search.start_year
        year_to = search.end_year

        download_url = Elsevier.URL_TEMPLATE.format(year_from=year_from, year_to=year_to, keyword=url_keyword,
                                                    page_count=Elsevier.PAGE_COUNT, offset='{offset}')
        articles_link_xpath = '//*[@id="srp-results-list"]/ol/li[contains(@class, "ResultItem") and boolean(@data-doi)]'
        article_link_relative_xpath = './/h2//a/@href'
        page_count_css_selector = '#srp-pagination > li:nth-child(1)'
        # try to fetch page count from page, or else default to constant
        try:
            # Use exponential backoff for requests
            if Elsevier.request_with_backoff(pw, download_url.format(offset=0)):
                page_count_text = pw.page.locator(page_count_css_selector).nth(0).text_content()
                if page_count_text is None:
                    page_count_text = ''
                page_count = int(page_count_text.strip().split(' ')[-1])
                h.log_line('Page count:', page_count)
            else:
                h.log_line('Failed to load initial page, using default page count')
                page_count = Config.number_of_pages_elsevier
        except TimeoutError as ex:
            h.log_line(ex)
            page_count = Config.number_of_pages_elsevier

        page_count = min(page_count, Config.number_of_pages_elsevier) # in case page number is more than constant
        try:
            data = []
            header = ['page', 'link', 'page_link', 'keyword', 'source', 'link_data']
            for page_num in range(1, page_count + 1):
                # Rotate context every 10 pages
                if page_num > 0 and page_num % 10 == 0:
                    pw.rotate_context()

                keyword_page_filename = keyword_page_template.format(page=page_num)
                offset = Elsevier.PAGE_COUNT * (page_num - 1)
                current_url = download_url.format(offset=offset)
                web_page, current_url = download_page_elsevier(pw, current_url, keyword_page_filename, search)
                links_on_page = web_page.xpath(articles_link_xpath)

                if len(links_on_page) == 0:
                    h.log_line('Breaking at page:', page_num, 'because no new links were found. Total links:',
                               len(links_unique))
                    break

                for link_on_page in links_on_page:
                    link = link_on_page.xpath(article_link_relative_xpath)
                    link = tools.clean_and_strip_string(link)
                    if link not in links_unique:
                        links_unique.add(link)
                        link = Elsevier.ABSOLUTE_URI + link  # The links are with relative path (that's why the concat)
                        link_data = etree.tostring(link_on_page)
                        data.append([page_num, link, current_url, keyword, Config.sources.get('elsevier'), link_data])
                        links.append([link, link_data])

                h.log_line('Page', page_num, 'of', Config.number_of_pages_elsevier, 'finished. Total links so far:',
                           len(links_unique))
                if len(links_unique) >= Config.max_papers_elsevier:
                    h.log_line('Breaking at page', page_num, 'because max papers:', Config.max_papers_elsevier,
                               'was reached. Total links:', len(links_unique))
                    break

            # save data in csv and excel formats
            df = pd.DataFrame(data=data, columns=header)
            hio.df_to_csv(df, keyword_urls_filename)
            h.csv_to_excel(keyword_urls_filename)

        except Exception as ex:
            h.log_line(ex)

        return links, keyword_links_filename

    DOI_XPATHS = ['@data-doi']
    TITLE_XPATHS = ['string(//h2//a)', 'string(h2/span/a)']
    DATE_XPATHS = ['//div[contains(@class, "SubType")]//span[contains(@class, "srctitle-date-fields")]/span[2]/text()']
    PUBLICATION_TITLE_XPATHS = ['//*[@id="publication-title"]/a/text()',
                                '//div[contains(@class, "SubType")]//span/a[contains(@class, "subtype-srctitle-link")]' 
                                '/span/span/text()']
    ABSTRACT_XPATH = '//div[contains(@class, "abstract") and contains(@class, "author")]'
    CITATION_XPATH = '//*[@id="citing-articles-header"]//h2'
    AUTHORS_XPATH = '//*[@id="author-group"]/button'
    AUTHOR_NAME_XPATH = './/span[contains(@class, "given-name") or contains(@class, "surname")]'
    AUTHOR_CARD_XPATH = '//*[@id="side-panel-author"]'
    AUTHOR_GIVEN_NAME_XPATHS = ['//*[@id="author-group"]/a//span[contains(@class, "given-name")]/text()']
    AUTHOR_SURNAME_NAME_XPATHS = ['//*[@id="author-group"]/a//span[contains(@class, "surname")]/text()']
    EMAIL_XPATH = '//div[contains(@class, "SidePanelAuthor")]//div[contains(@class, "e-address")]'
    AFFILIATION_SHOW_MORE_BUTTON_XPATH = '//*[@id="show-more-btn"]'
    AFFILIATION_XPATH = '//*[@id="author-group"]/dl[contains(@class, "affiliation")]//dd'

    @staticmethod
    def _scrape_article_page(
            search: SearchConfig,
            url: str,
            keyword: str,
            article_html: str,
            pw: PlaywrightBrowser,
            lock: Lock
    ) -> Optional[Tuple[Any, ...]]:
        h.log_line(f'Starting to process article on url: {url} found for keyword: {keyword} for Elsevier database.')
        Elsevier_source = Config.sources.get('elsevier', 'Elsevier')
        doc = html.fromstring(article_html)

        # --- static HTML extraction (same as before) ---
        title = Elsevier.find_xpath_in_html(doc, Elsevier.TITLE_XPATHS).strip()
        doi_raw = Elsevier.find_xpath_in_html(doc, Elsevier.DOI_XPATHS)
        doi_clean = tools.clean_and_strip_string(doi_raw).replace('https://doi.org/', '')
        valid_doi = tools.extract_doi(doi_clean) or tools.simplify_url(url) or h.remove_nonalpha(title, '')
        publication_title = tools.clean_and_strip_string(
            Elsevier.find_xpath_in_html(doc, Elsevier.PUBLICATION_TITLE_XPATHS))
        date = tools.clean_and_strip_string(Elsevier.find_xpath_in_html(doc, Elsevier.DATE_XPATHS))
        try:
            year = int(date[-4:])
        except:
            h.log_line("invalid year:", date, "in", url)
            year = 0

        # defaults
        abstract = ''
        authors = emails = affiliations = []
        number_of_authors = number_of_citations = 0

        article_filename = tools.html_filename(url, search.folder_Elsevier_articles)
        data_filename = tools.json_filename(url, search.folder_Elsevier_Data)

        # --- cache check ---
        if search.delete_cache and os.path.isfile(data_filename):
            os.remove(data_filename)
        if os.path.isfile(data_filename) and os.stat(data_filename).st_size > 0:
            h.log_line('File exists:', data_filename, 'Skipping download of', url)
            data = json.load(open(data_filename, 'r', encoding='utf-8'))
            title = data['title']
            valid_doi = data['doi']
            publication_title = data['publication_title']
            date = data['date']
            year = data['year']
            abstract = data['abstract']
            number_of_citations = data['number_of_citations']
            authors = data['authors']
            emails = data['emails']
            affiliations = data['affiliations']
            number_of_authors = data['number_of_authors']
            h.log_line(f'Elsevier data caching for article: {url}')

        else:
            # --- dynamic extraction with Playwright ---
            try:
                # Use exponential backoff strategy for requests
                if not Elsevier.request_with_backoff(pw, url):
                    h.log_line(f"Failed to load article page after {Elsevier.max_attempts} attempts: {url}")
                    with lock:
                        search.result_counts[Elsevier_source][Config.PRISMA_parsing_errors] += 1
                    return None

                # abstract
                try:
                    pw.page.wait_for_selector(Elsevier.ABSTRACT_XPATH, timeout=Config.browser_delay_time_elsevier * 1000)
                    abs_nodes = pw.page.locator(Elsevier.ABSTRACT_XPATH).all()
                    abstract = ' '.join([n.text_content() or '' for n in abs_nodes])
                    abstract = tools.clean_and_strip_string(abstract)
                except TimeoutError:
                    h.log_line('Abstract for url', url, 'is not available.')
                    with lock:
                        search.result_counts[Elsevier_source][Config.PRISMA_parsing_errors] += 1
                    return None

                # citations
                try:
                    cit_text = pw.page.locator(Elsevier.CITATION_XPATH).text_content() or ''
                    num = cit_text[cit_text.find('(') + 1: cit_text.find(')')]
                    number_of_citations = int(num)
                except Exception:
                    h.log_line('Citations missing or malformed for url', url)
                    number_of_citations = 0

                # authors + emails
                authors_list = []
                emails_list = []
                try:
                    pw.page.wait_for_selector(Elsevier.AUTHORS_XPATH, timeout=Config.browser_delay_time_elsevier * 1000)
                    for author_el in pw.page.locator(f'xpath={Elsevier.AUTHORS_XPATH}').all():
                        # names
                        # name_parts = author_el.locator(Elsevier.AUTHOR_NAME_XPATH).all()
                        name_parts = author_el.locator('css=.given-name, .surname').all()
                        name = ' '.join([n.text_content() or '' for n in name_parts])
                        authors_list.append(tools.clean_and_strip_string(name))

                        # click to open card & get email
                        author_el.click()
                        try:
                            pw.page.wait_for_selector(Elsevier.AUTHOR_CARD_XPATH,
                                                   timeout=Config.browser_delay_time_elsevier * 1000)
                            # email = page.locator(Elsevier.EMAIL_XPATH).text_content() or ''
                            email = pw.page.locator('css=.SidePanelAuthor .e-address').text_content(timeout=3000) # less timeout here because email is frequently missing
                            email = tools.clean_and_strip_string(email)
                            if h.is_email_valid(email):
                                emails_list.append(email)
                        except TimeoutError:
                            h.log_line('Email not available for url', url)
                except TimeoutError:
                    h.log_line('Authors for url', url, 'are not available.')

                number_of_authors = len(authors_list)
                authors = ','.join(authors_list)
                emails = ';'.join(emails_list)

                # affiliations
                affiliations_list = []
                try:
                    pw.page.wait_for_selector(Elsevier.AFFILIATION_SHOW_MORE_BUTTON_XPATH,
                                           timeout=Config.browser_delay_time_elsevier * 1000)
                    pw.page.locator(Elsevier.AFFILIATION_SHOW_MORE_BUTTON_XPATH).click()
                    pw.page.wait_for_selector(Elsevier.AFFILIATION_XPATH,
                                           timeout=Config.browser_delay_time_elsevier * 1000)
                    for aff in pw.page.locator(Elsevier.AFFILIATION_XPATH).all():
                        affiliations_list.append(tools.clean_and_strip_string(aff.text_content() or ''))
                except TimeoutError:
                    h.log_line('Affiliations for url', url, 'are not available.')

                affiliations = ';'.join(affiliations_list)

            except Exception as ex:
                h.log_line('Dynamic content load failed for', url, ex)

            finally:
                # save JSON cache
                data = {
                    "title": title,
                    "doi": valid_doi,
                    "publication_title": publication_title,
                    "date": date,
                    "year": year,
                    "abstract": abstract,
                    "number_of_citations": number_of_citations,
                    "authors": authors,
                    "emails": emails,
                    "affiliations": affiliations,
                    "number_of_authors": number_of_authors
                }
                with open(data_filename, 'w', encoding='utf-8') as fj:
                    json.dump(data, fj, ensure_ascii=False)

            try:
                # save HTML
                with open(article_filename, 'w', encoding='utf-8') as fout:
                    fout.write(pw.page.content())
            except Error as e:
                h.log_line('Error saving article HTML to file:', article_filename, e)


        # post-process affiliations → countries
        if h.is_empty(affiliations):
            affiliations = ''
            number_different_affiliations = countries = number_different_countries = 0
        else:
            (affiliations, number_different_affiliations,
             countries, number_different_countries) = Countries.process_affiliations(affiliations)

        number_different_countries = min(number_of_authors, number_different_countries)

        fields = (
            valid_doi, url, title, authors, date, year,
            number_of_citations, abstract, keyword, Elsevier_source,
            publication_title, affiliations, number_different_affiliations,
            countries, number_different_countries,
            number_of_authors, emails
        )

        # final validation
        if h.is_empty(title) or h.is_empty(authors) or len(abstract) <= Config.abstract_min_length:
            with lock:
                search.result_counts[Elsevier_source][Config.PRISMA_parsing_errors] += 1
                search.parsing_errors_articles.append(fields)
            h.log_line('Skipping to process article for url:', url, 'because incomplete.')
            return fields

        if h.is_empty(valid_doi):
            with lock:
                search.parsing_errors_articles.append(fields)

        h.log_line('Finished processing article on url', url)
        return fields

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
            # Calculate delay with exponential backoff
            base_delay = random.uniform(Elsevier.random_delay_min, Elsevier.random_delay_max)
            delay = base_delay * (Elsevier.backoff_factor ** (attempt - 1))

            h.log_line(f"Request attempt {attempt} for {url}. Waiting {delay:.2f} seconds...")
            time.sleep(delay)

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
            if attempt < Elsevier.max_attempts:
                h.log_line(f"Retrying... (Attempt {attempt + 1} of {Elsevier.max_attempts})")
                return Elsevier.request_with_backoff(pw, url, attempt + 1, wait_until, timeout)
            else:
                h.log_line(f"Max attempts ({Elsevier.max_attempts}) reached. Giving up on: {url}")
                return False
