import os
from typing import Set, Tuple, List, Optional
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright, TimeoutError
from slugify import slugify
import pandas as pd
from nordvpn_switcher import initialize_VPN, rotate_VPN, terminate_VPN

from configuration.config import Config
from core.search_config import SearchConfig
from help_tools import helpers as h, hio
from help_tools.browser_emulate import create_playwright_browser, PlaywrightBrowser, download_page_acm
from help_tools.countries import Countries
from help_tools.tools import tools


class ACM:

    # CONSTANTS
    ABSOLUTE_URI = 'https://dl.acm.org'
    URL_TEMPLATE = ABSOLUTE_URI + '/action/doSearch?AllField={keyword}&pageSize=50&AfterYear={year_from}' \
                                  '&BeforeYear={year_to}&startPage={page}'

    PAGE_DOWNLOAD_COUNTER = 0
    PAGE_DOWNLOAD_COUNTER_LIMIT = 50
    random_delay_min = 1.5
    random_delay_max = 4
    max_attempts = 2
    backoff_factor = 2
    # INSTRUCTIONS = initialize_VPN(area_input=['random countries europe 30'])

    @staticmethod
    def crawl(search: SearchConfig, keyword: str = None, force_crawl: bool = False):
        """
        The public method to call for crawling the ACM database by the search configuration provided.

        :param search: An object that contains all information about the crawling
        :type search: SearchConfig
        :param keyword: A keyword for crawling (Optional parameter)
        :type keyword: str
        :param force_crawl: If True, the method will crawl again for each keyword even if some old results already exist
        :type force_crawl: bool
        """

        # write into status and log files and set default for result counts
        # ACM.check_ip_rotation()
        with sync_playwright() as p:
            pw = create_playwright_browser(playwright=p)
            try:
                search.set_status(key='ACM', value='Starting')
                h.log_line('Starting crawling for ACM.')
                search.set_result_counts(sources=Config.sources.get('acm', 'ACM'))

                # Iterate through all keywords and process them one by one by getting all the articles and scrape each of them
                if keyword is not None:
                    ACM._process_keyword(search, keyword, search.force_crawl, pw)
                else:
                    for keyword in search.keywords:
                        ACM._process_keyword(search, keyword, search.force_crawl, pw)

                search.set_status(key='ACM', value='Completed')
                h.log_line('Finished crawling for ACM.')
                search.to_pickle()
            finally:
                pw.context.close()
                pw.browser.close()

    @staticmethod
    def _process_keyword(search: SearchConfig, keyword: str, force_crawl: bool, pw: PlaywrightBrowser):
        """
        Process the ACM database for a certain keyword and store all results in a file.

        :param search: An object that contains all information about the crawling
        :type search: SearchConfig
        :param keyword: The keyword used for crawling
        :type keyword: str
        :param force_crawl: If True, the method will crawl again for each keyword even if some old results already exist
        :type force_crawl: bool
        """

        # write into log files
        h.log_line(f'Starting to process keyword {keyword} for ACM database.')

        links, links_filename = ACM._crawl_keyword(search, keyword, force_crawl, pw)

        # TODO: This is commented because if there is re-running and the links file already exists we lose search config
        # TODO: result counts
        # if os.path.isfile(links_filename) and os.stat(links_filename).st_size > 0 and not force_crawl:
        #     h.log_line('File exists: ', links_filename)
        #     h.log_line('Skipping ACM processing for keyword:', keyword)
        #     return

        # scrape pages here
        articles_data = []
        for link in links:
            article_data = ACM._scrape_article_page(search, link, pw, keyword)
            if article_data:
                articles_data.append(article_data)
        search.write_results(articles_data, links_filename)
        # terminate_VPN(instructions=None)

        # write into log files
        h.log_line(f'Finished processing keyword {keyword} for ACM database.')

    @staticmethod
    def _crawl_keyword(search: SearchConfig, keyword: str, force_crawl: bool, pw: PlaywrightBrowser) -> Tuple[Set[str], str]:
        """
        Crawl the ACM database for a certain keyword and store all results in a file.

        :param search: An object that contains all information about the crawling
        :type search: SearchConfig
        :param keyword: The keyword used for crawling
        :type keyword: str
        :param force_crawl: If True, the method will crawl again for each keyword even if some old results already exist
        :type force_crawl: bool

        :return: All links for the articles found for the keyword and the filename where the link results will be stored
        :rtype: Tuple[Set[str], str]
        """

        # define folder and file names and create folders
        keyword_slug = slugify(keyword)
        keyword_folder = os.path.join(search.folder_ACM_Links, keyword_slug)
        h.create_folder(keyword_folder)
        keyword_urls_filename = os.path.join(keyword_folder, keyword_slug + '_urls_only.csv')
        keyword_page_template = os.path.join(keyword_folder, keyword_slug + '_page-{page}.txt')
        keyword_links_filename = os.path.join(keyword_folder, keyword_slug + '_links.csv')

        # Return previously crawled results if force crawl is negative
        if os.path.isfile(keyword_urls_filename) and os.stat(keyword_urls_filename).st_size > 0 \
                and force_crawl is False:
            h.log_line('File exists: ', keyword_urls_filename)
            h.log_line('Skipping ACM download of ', keyword)
            h.log_line('Reading from file: ', keyword_urls_filename)
            links_df = hio.pd_read_csv_or_string_stream(filename=keyword_urls_filename, encoding='UTF-8')
            links = links_df['link'].tolist()
            return links, keyword_links_filename

        links = set()
        url_keyword = ' AND '.join(keyword.split())  # Otherwise it uses OR by default
        url_keyword = quote_plus(url_keyword)
        year_from = search.start_year
        year_to = search.end_year
        download_url = ACM.URL_TEMPLATE.format(year_from=year_from, year_to=year_to, keyword=url_keyword, page='{page}')
        items_links_xpath = '//*[@id="pb-page-content"]//li[contains(@class, "issue-item-container")]'
        i_type_xpath = './/div[contains(@class, "issue-item__citation")]/div[contains(@class, "issue-heading")]/text()'
        # article_link_xpath = './/h5//a/@href'
        article_link_xpath = './/div[contains(@class, "issue-item__content")]//h3//a/@href'

        try:
            data = []
            header = ['page', 'link', 'page_link', 'keyword', 'source']
            for page in range(0, Config.number_of_pages_acm + 1):
                keyword_page_filename = keyword_page_template.format(page=page)
                current_url = download_url.format(page=page)
                # web_page, current_url = tools.download_page(current_url, keyword_page_filename, search, add_headers=True)
                # ACM.check_ip_rotation()
                web_page, current_url = download_page_acm(pw, current_url, keyword_page_filename, search)
                items_on_page = web_page.xpath(items_links_xpath)

                if len(items_on_page) == 0:
                    h.log_line('Breaking at page:', page + 1, 'because no new links were found. Total links:',
                               len(links))
                    break

                for item in items_on_page:
                    item_type = item.xpath(i_type_xpath)
                    item_type = tools.clean_and_strip_string(item_type)
                    if item_type not in ('proceeding', 'book'):
                        link = item.xpath(article_link_xpath)
                        link = tools.clean_and_strip_string(link)
                        if link not in links:
                            link = ACM.ABSOLUTE_URI + link  # The links are with relative path (that's why the concat)
                            links.add(link)
                            data.append([page + 1, link, current_url, keyword, Config.sources.get('acm')])

                h.log_line('Page', page + 1, 'of', Config.number_of_pages_acm, 'finished. Total links so far:',
                           len(links))
                if len(links) >= Config.max_papers_acm:
                    h.log_line('Breaking at page', page + 1, 'because max papers:', Config.max_papers_acm,
                               'was reached. Total links:', len(links))
                    break

            # save data in csv and excel formats
            df = pd.DataFrame(data=data, columns=header)
            hio.df_to_csv(df, keyword_urls_filename)
            h.csv_to_excel(keyword_urls_filename)

        except Exception as ex:
            h.log_line(ex)

        return links, keyword_links_filename

    TITLE_XPATHS = ['//*[@id="pb-page-content"]//h1[contains(@class,"citation__title")]/text()',
                    '//*[@id="pb-page-content"]//h1[@property="name"]/text()',
                    '//*[@id="pb-page-content"]/div/main/div[2]/article/div[1]/div[2]/div/div[2]/h1/text()']

    DOI_XPATHS = [
                  '//div[contains(@class,"core-self-citation")]//div[contains(@class, "doi")]//a/text()',
                  '//*[@id="pb-page-content"]//a[contains(@class,"issue-item__doi")]/text()',
                  '//*[@id="pb-page-content"]//div[contains(@class,"doi")]/a/text()',
                  '//*[@id="pb-page-content"]/div/main/div[2]/article/div[1]/div[2]/div/div[4]/div/span[4]/a/text()']

    AUTHORS_XPATHS = [
                      '//span[contains(@class, "auth-name")]/a/text()',
                      '//span[contains(@class, "auth-name")]/text()',
                      '//div[contains(@class,"contributors")]//span[@property="author"]//a/@title',
                      ]

    DATE_XPATHS = [
                   '//div[contains(@class,"core-published")]//span[contains(@class, core-date-published)]/text()',
                   '//*[@id="pill-information__content"]//div[contains(@class,"cover-date")]/text()',
                   '//*[@id="pb-page-content"]//span[contains(@class,"epub-section__date")]/text()']

    CITATIONS_XPATHS = ['//div[contains(@class, "info-panel")]//span[contains(@class, "citation")]/span[1]/text()',
                        '//*[@id="pill-citations__contentcon"]/span/text()',
                        '//*[@id="pill-bibliometrics__content"]//div[contains(@class,"citation")]',
                        '/div[contains(@class,"metric-value")]/span/text()']

    ABSTRACT_XPATHS = ['//section[@id="abstract"]/div[@role="paragraph"]/text()',
                       '//*[@id="pb-page-content"]//div[contains(@class,"abstractInFull")]/p/text()',
                       '//*[@id="pb-page-content"]/div/main/div[2]/article/div[2]/div[2]/div[2]/div[1]',
                       '/div/div[2]/p/text()']

    PUBLICATION_TITLE_XPATHS = ['//div[contains(@class, "core-self-citation")]//div[contains(@class, "core-enumeration")]//span[@property="name"]/text()',
                                '//div[contains(@class, "core-self-citation")]//a[@property="name"]/text()',
                                '//*[@id="pill-information__content"]//div[contains(@class,"book-meta")]/text()',
                                '//*[@id="pb-page-content"]//span[contains(@class,"epub-section__title")]/text()']

    AFFILIATIONS_XPATHS = ['//span[contains(@class,"info--text") and contains(@class, "auth-institution")]/text()',
                           '//div[contains(@class,"authors-accordion")]//div[@id="sb-1"]',
                           '//span[contains(@class,"loa_author_inst")]/p/text()',
                           '//*[@id="pill-authors__content"]//span[contains(@class,"auth-institution")]/text()']
    AUTHORS_PANE_BUTTON_XPATH = '//div[contains(@class, "contributors")]/a[contains(@class, "to-authors-affiliations")]'
    AUTHORS_PANE_CONTAINER_XPATH = '//div[@id="core-collateral-info"]//div[contains(@class, "pubContribs")]'

    @staticmethod
    def _scrape_article_page(search: SearchConfig, url: str, pw: PlaywrightBrowser, keyword: str = None) -> Optional[Tuple[str, ...]]:
        """
        Scrape an article page from the ACM database and return tuple with extracted values

        :param search: An object that contains all information about the crawling
        :type search: SearchConfig
        :param url: The URL where the article is located
        :type url: str
        :param keyword: The keyword used for crawling
        :type keyword: str

        :return: Extracted values from the article page
        :rtype: Optional[Tuple[str,..]]
        """

        # write to log files
        h.log_line(f'Starting to process article on url: {url} found for keyword: {keyword} for ACM database.')

        ACM_source = Config.sources.get('acm', 'ACM')
        # search.result_counts[ACM_source][Config.PRISMA_considered] += 1
        article_filename = tools.html_filename(url, search.folder_ACM_Articles)
        fields = None

        try:
            # web_page, final_url = tools.download_page(url, article_filename, search, add_headers=True)
            # ACM.check_ip_rotation()

            web_page, final_url = download_page_acm(pw, url, article_filename, search, is_article_page=True)

            # Do not process the article if the URL is already processed by another source
            # if keyword is not None and search.exists_url(final_url, ACM_source):
            #     search.result_counts[ACM_source][Config.PRISMA_duplicates] += 1
            #     h.log_line('Skipping to process article for url:', url,
            #                'because it is already processed by this or another source.')
            #     return fields

            # extract title from the article
            title = ACM.find_xpath_in_html(web_page, ACM.TITLE_XPATHS)
            if title is not None:
                title = tools.clean_and_strip_string(title)
            else:
                title = ''

            # extract the DOI from the article
            doi = ACM.find_xpath_in_html(web_page, ACM.DOI_XPATHS)
            doi = tools.clean_and_strip_string(doi).replace('https://doi.org/', '')
            if h.is_empty(doi):
                _doi = tools.simplify_url(final_url)
                if len(_doi) > 0:
                    doi = _doi
                else:
                    doi = h.remove_nonalpha(title, '')

            # # extract authors from the article
            # authors = ACM.find_xpath_in_html(web_page, ACM.AUTHORS_XPATHS)
            # if authors is not None:
            #     authors = [tools.clean_and_strip_string(str(author)) for author in authors]
            # else:
            #     authors = []
            # number_of_authors = len(authors)
            # authors = ','.join(authors)

            # extract dates from the article
            date = ACM.find_xpath_in_html(web_page, ACM.DATE_XPATHS)
            if date is not None:
                date = tools.clean_and_strip_string(date)
                year = date[-4:]
            else:
                year = ''
                date = ''

            # Do not process the article if the year it was published is not between the specified range
            # if not search.start_year <= int(year) <= search.end_year:
            #     search.result_counts[ACM_source][Config.PRISMA_invalid_years] += 1
            #     h.log_line('Skipping to process article for url:', url,
            #                'because the year is invalid.')
            #     return fields

            # extract number of citations from the article
            number_of_citations = ACM.find_xpath_in_html(web_page, ACM.CITATIONS_XPATHS)
            if number_of_citations is not None:
                number_of_citations = tools.clean_and_strip_string(number_of_citations)
            else:
                number_of_citations = 0

            # extract the abstract from the article
            abstract = ACM.find_xpath_in_html(web_page, ACM.ABSTRACT_XPATHS)
            if abstract is not None:
                abstract = tools.clean_and_strip_string(abstract)
            else:
                abstract = ''

            # extract the publication title where the article was published
            publication_title = ACM.find_xpath_in_html(web_page, ACM.PUBLICATION_TITLE_XPATHS)
            if publication_title is not None:
                publication_title = tools.clean_and_strip_string(publication_title)
            else:
                publication_title = ''

            affiliations = []
            number_different_affiliations = 0
            countries = []
            number_different_countries = 0
            authors = []
            number_of_authors = 0
            try:
                # pw.page.locator(f'xpath={ACM.AUTHORS_PANE_BUTTON_XPATH}').click(timeout=5000)
                affiliations = ACM.find_xpath_in_html(web_page, ACM.AFFILIATIONS_XPATHS)
                if affiliations is not None:
                    affiliations = [tools.clean_and_strip_string(str(affiliation)) for affiliation in affiliations]
                else:
                    affiliations = []
                affiliations = ';'.join(affiliations)

                authors = ACM.find_xpath_in_html(web_page, ACM.AUTHORS_XPATHS)
                if authors is not None:
                    authors = [tools.clean_and_strip_string(str(author)) for author in authors]
                else:
                    authors = []
                number_of_authors = len(authors)
                authors = ','.join(authors)
            except TimeoutError as ex:
                h.log_line('Error while trying to click on the authors pane:', ex)
            except Exception as ex:
                h.log_line('Error while trying to click on the authors pane:', ex)
            # extract the affiliations and the countries from the article
            if h.is_empty(affiliations):
                affiliations, number_different_affiliations, countries, number_different_countries = '', 0, '', 0
            else:
                (affiliations, number_different_affiliations,
                 countries, number_different_countries) = Countries.process_affiliations(affiliations)

            # Do not process the article if there is no information about the title, the authors or the abstract
            if h.is_empty(title) or h.is_empty(authors) or len(abstract) <= Config.abstract_min_length:
                search.result_counts[ACM_source][Config.PRISMA_parsing_errors] += 1
                h.log_line('Skipping to process article for url:', url,
                           'because the data is incomplete.')
                return fields

            # There may be wrong calculation because of irregular affiliation writing
            if number_different_countries > number_of_authors:
                number_different_countries = number_of_authors

            emails = None

            fields = (doi, final_url, title, authors, date, year, number_of_citations, abstract,
                      keyword, ACM_source, publication_title, affiliations, number_different_affiliations,
                      countries, number_different_countries, number_of_authors, emails)
            h.log_line('Finished with processing article on url', url, 'found for keyword:', keyword,
                       'for ACM database.')

        except Exception as ex:
            h.log_line('Error while trying to scrape the article page:', url, ex)

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
    def check_ip_rotation():
        """
        Increment the download page counter, and if it is bigger than the limit, change the IP address.
        """
        pass
        # ACM.PAGE_DOWNLOAD_COUNTER += 1
        # print(ACM.PAGE_DOWNLOAD_COUNTER)
        # if ACM.PAGE_DOWNLOAD_COUNTER >= ACM.PAGE_DOWNLOAD_COUNTER_LIMIT:
        #     ACM.PAGE_DOWNLOAD_COUNTER = 0
        #     rotate_VPN(ACM.INSTRUCTIONS)
