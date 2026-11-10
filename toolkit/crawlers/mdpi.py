import json
import os
import threading
from threading import Lock
from typing import Set, Tuple, List, Optional, Any
from urllib.parse import quote_plus
import pandas as pd

from slugify import slugify

from configuration.config import *
from help_tools.countries import Countries
from core.search_config import SearchConfig
from help_tools import helpers as h, hio
from help_tools.tools import tools


class MDPI:
    # CONSTANTS
    ABSOLUTE_URI = 'https://www.mdpi.com'
    URL_TEMPLATE = ABSOLUTE_URI + '/search?sort=relevance&page_no={page}&year_from={y_from}&year_to={y_to}&q={keyword}'\
                                  '&page_count=15&view=compact'

    @staticmethod
    def crawl(search: SearchConfig, lock: Lock = threading.Lock(), keyword: str = None, force_crawl: bool = False):
        """
        The public method to call for crawling the MDPI database by the search configuration provided.

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
            search.set_status(key='MDPI', value='Starting')
            h.log_line('Starting crawling for MDPI.')
            search.set_result_counts(sources=Config.sources.get('mdpi', 'MDPI'))

        # Iterate through all keywords and process them one-by-one by getting all the articles and scraping each of them
        if keyword is not None:
            MDPI._process_keyword(search, keyword, lock, search.force_crawl)
        else:
            for keyword in search.keywords:
                MDPI._process_keyword(search, keyword, lock, search.force_crawl)
        with lock:
            search.set_status(key='MDPI', value='Completed')
            h.log_line('Finished crawling for MDPI.')
            search.to_pickle()

    @staticmethod
    def _process_keyword(search: SearchConfig, keyword: str, lock, force_crawl: bool):
        """
        Process the MDPI database for a certain keyword and store all results in a file.

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
        h.log_line(f'Starting to process keyword {keyword} for MDPI database.')

        links, links_filename = MDPI._crawl_keyword(search, keyword, force_crawl)

        # scrape pages here
        articles_data = []
        for link in links:
            article_data = MDPI._scrape_article_page(search, link, lock, keyword)
            if article_data:
                articles_data.append(article_data)
                if len(articles_data) >= Config.max_papers_mdpi:
                    h.log_line('Breaking scraping articles for', Config.sources['mdpi'], 'because max papers:',
                               Config.max_papers_mdpi, 'was reached.', 'Total scraped articles:', len(articles_data))
                    break
        with lock:
            search.write_results(articles_data, links_filename)

        # write into log files
        h.log_line(f'Finished processing keyword {keyword} for MDPI database.')

    @staticmethod
    def _crawl_keyword(search: SearchConfig, keyword: str, force_crawl: bool) -> Tuple[Set[str], str]:
        """
        Crawl the MDPI database for a certain keyword and store all results in a file.

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
        keyword_folder = os.path.join(search.folder_MDPI_links, keyword_slug)
        h.create_folder(keyword_folder)
        keyword_urls_filename = os.path.join(keyword_folder, keyword_slug + '_urls_only.csv')
        keyword_page_template = os.path.join(keyword_folder, keyword_slug + '_page-{page}.txt')
        keyword_links_filename = os.path.join(keyword_folder, keyword_slug + '_links.csv')
        h.create_folder(search.folder_MDPI_data)

        # Return previously crawled results if force crawl is negative
        if os.path.isfile(keyword_urls_filename) and os.stat(keyword_urls_filename).st_size > 0 \
                and search.force_crawl is False:
            h.log_line('File exists: ', keyword_urls_filename)
            h.log_line('Skipping MDPI download of ', keyword)
            h.log_line('Reading from file: ', keyword_urls_filename)
            links_df = hio.pd_read_csv_or_string_stream(filename=keyword_urls_filename, encoding='UTF-8')
            links = links_df['link'].tolist()
            return links, keyword_links_filename

        links = set()
        url_keyword = quote_plus(keyword)
        from_ = search.start_year
        to_ = search.end_year
        download_url = MDPI.URL_TEMPLATE.format(y_from=from_, y_to=to_, keyword=url_keyword, page='{page}')
        articles_links_xpath = '//*[@id="exportArticles"]//a[@class="title-link"]/@href'
        try:
            data = []
            header = ['page', 'link', 'page_link', 'keyword', 'source']
            for page in range(1, Config.number_of_pages_mdpi + 1):
                keyword_page_filename = keyword_page_template.format(page=page)
                current_url = download_url.format(page=page)
                web_page, current_url = tools.download_page(current_url, keyword_page_filename, search=search, add_headers=True)
                links_on_page = web_page.xpath(articles_links_xpath)

                if len(links_on_page) == 0:
                    h.log_line('Breaking at page:', page, 'because no new links were found. Total links:', len(links))
                    break

                for link in links_on_page:
                    if link not in links:
                        link = MDPI.ABSOLUTE_URI + link  # The links are with relative path (that's why the concat)
                        links.add(link)
                        data.append([page, link, current_url, keyword, Config.sources.get('mdpi')])

                h.log_line('Page', page, 'of', Config.number_of_pages_mdpi, 'finished. Total links so far:', len(links))
                if len(links) >= Config.max_papers_mdpi:
                    h.log_line('Breaking at page', page, 'because max papers:', Config.max_papers_mdpi, 'was reached.',
                               'Total links:', len(links))
                    break

            # save data in csv and excel formats
            df = pd.DataFrame(data=data, columns=header)
            hio.df_to_csv(df, keyword_urls_filename)
            h.csv_to_excel(keyword_urls_filename)

        except Exception as ex:
            h.log_line(ex)

        return links, keyword_links_filename

    DOI_XPATHS = ['//*[@id="abstract"]//div[contains(@class, "bib-identity")]/a/text()',
                  '//*[@id="abstract"]/div[2]/div[6]/a/text()']

    TITLE_XPATHS = ['//*[@id="abstract"]//h1[contains(@class,"title ")]/text()',
                    '//*[@id="abstract"]/div[2]/h1/text()']

    AUTHORS_XPATHS = ['//*[@id="abstract"]/div[2]/div[2]/span/div/a/span/text()',
                      '//*[contains(@class, "sciprofiles-link__name")]/text()']

    DATE_XPATHS = ['//*[contains(text(), "Published:")]/text()']

    ABSTRACT_XPATHS = ['//*[@id="html-abstract"]//div[contains(@class, "html-p")]/text()',
                       '//*[@id="abstract"]//div[contains(@class, "art-abstract")]/text()',
                       '//*[@id="abstract"]/div[3]/div[2]/div[1]/text()']

    PUBLICATION_TITLE_XPATHS = ['//*[@id="abstract"]//div[contains(@class, "belongsTo")]/a/text()',
                                '//*[@id="abstract"]/div[2]/div[8]/a/text()',
                                '//*[@id="abstract"]//div[contains(@class, "bib-identity")]/em[1]/text()']

    AFFILIATIONS_XPATHS = ['//*[@id="abstract"]//div[contains(@class, "affiliation-name")]/text()']

    @staticmethod
    def _scrape_article_page(search: SearchConfig, url: str, lock: threading.Lock,
                             keyword: str = None) -> Optional[Tuple[Any, ...]]:
        """
        Scrape an article page from the MDPI database and return tuple with extracted values

        :param search: An object that contains all information about the crawling
        :type search: SearchConfig
        :param url: The URL where the article is located
        :type url: str
        :param lock: A Lock object used for protection of search object
        :type lock: Lock
        :param keyword: The keyword used for crawling
        :type keyword: str

        :return: Extracted values from the article page
        :rtype: Optional[Tuple[str,..]]
        """

        # write to log files
        h.log_line(f'Starting to process article on url: {url} found for keyword: {keyword} for MDPI database.')

        MDPI_source = Config.sources.get('mdpi', 'MDPI')
        article_filename = tools.html_filename(url, search.folder_MDPI_articles)
        data_filename = tools.json_filename(url, search.folder_MDPI_data)

        if search.delete_cache and os.path.isfile(data_filename):
            os.remove(data_filename)

        if os.path.isfile(data_filename) and os.stat(data_filename).st_size > 0:
            # json file exists, skipping download of page

            with open(data_filename, 'r') as fin:
                data = json.load(fin)

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
            number_different_affiliations = data['number_of_affiliations']
            countries = data['countries']
            number_different_countries = data['number_of_countries']
            final_url = data['final_url']

            h.log_line(f'MDPI data caching for article: {url} and keyword: {keyword}')

        else:
            title = valid_doi = publication_title = date = year = abstract = number_of_citations = authors = None
            emails = affiliations = number_of_authors = number_different_affiliations = countries = None
            number_different_countries = final_url = None
            try:
                web_page, final_url = tools.download_page(url, article_filename, add_headers=True)

                # extract title from the article
                title = MDPI.find_xpath_in_html(web_page, MDPI.TITLE_XPATHS)
                title = tools.clean_and_strip_string(title)

                # extract the DOI from the article
                doi = MDPI.find_xpath_in_html(web_page, MDPI.DOI_XPATHS)
                doi = tools.clean_and_strip_string(doi).replace('https://doi.org/', '')
                valid_doi = tools.extract_doi(doi)
                if h.is_empty(valid_doi):
                    _doi = tools.simplify_url(final_url)
                    if len(_doi) > 0:
                        valid_doi = _doi
                    else:
                        valid_doi = h.remove_nonalpha(title, '')

                # extract authors from the article
                authors = MDPI.find_xpath_in_html(web_page, MDPI.AUTHORS_XPATHS)
                authors = [tools.clean_and_strip_string(str(author)) for author in authors]
                number_of_authors = len(authors)
                authors = ','.join(authors)

                # extract emails from the article
                # TODO: extract emails
                emails = None

                published_date = MDPI.find_xpath_in_html(web_page, MDPI.DATE_XPATHS)
                published_date = tools.clean_and_strip_string(published_date).split('/')
                # published = ['Published:', 'day', 'month', 'year']
                published = str(published_date[0]).split(' ')
                year = published[-1]
                published = published[1:]
                date = ' '.join(published)

                # Do not process the article if the year it was published is not between the specified range
                try:
                    year = int(year)
                except Exception as date_ex:
                    h.log_line('Error while trying to extract date for url:', url, published_date, date, date_ex)
                    search.result_counts[MDPI_source][Config.PRISMA_parsing_errors] += 1
                    return None

                # extract number of citations from the article
                number_of_citations = None
                citations_url = final_url + '/stats'
                citations = tools.get_data_from_api(url=citations_url, folder=search.folder_MDPI_stats, add_headers=False)
                if citations:
                    number_of_citations = citations.get('metrics', {}).get('citations', number_of_citations)

                # extract the abstract from the article
                abstract = MDPI.find_xpath_in_html(web_page, MDPI.ABSTRACT_XPATHS)
                abstract = tools.clean_and_strip_string(abstract)

                # extract the publication title where the article was published
                publication_title = MDPI.find_xpath_in_html(web_page, MDPI.PUBLICATION_TITLE_XPATHS)
                publication_title = tools.clean_and_strip_string(publication_title)

                # extract the affiliations and the countries from the article
                affiliations = MDPI.find_xpath_in_html(web_page, MDPI.AFFILIATIONS_XPATHS)
                affiliations = [str(affiliation) for affiliation in affiliations]
                if affiliations[-1].startswith('Author'):  # Author to whom correspondence should be addressed.
                    affiliations = affiliations[:-1]
                if len(affiliations) > 1 and affiliations[-2].startswith('Author'):  # Author to whom correspondence...
                    affiliations = affiliations[:-2]
                affiliations = ';'.join(affiliations)
                if h.is_empty(affiliations):
                    affiliations, number_different_affiliations, countries, number_different_countries = '', 0, '', 0
                else:
                    (affiliations, number_different_affiliations,
                     countries, number_different_countries) = Countries.process_affiliations(affiliations)

                if number_different_countries > number_of_authors:
                    number_different_countries = number_of_authors

                h.log_line('Finished with processing article on url', url, 'found for keyword:', keyword,
                           'for MDPI database.')

            except Exception as ex:
                h.log_line('Error while trying to scrape the article page:', url, ex)
            finally:
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
                        "number_of_authors": number_of_authors,
                        "number_of_affiliations": number_different_affiliations,
                        "countries": countries,
                        "number_of_countries": number_different_countries,
                        "final_url": final_url
                         }
                data_dict = json.dumps(data)
                with open(data_filename, 'w', encoding='UTF-8') as fj:
                    fj.write(data_dict)

        fields = (valid_doi, final_url, title, authors, date, year, number_of_citations, abstract,
                  keyword, MDPI_source, publication_title, affiliations, number_different_affiliations,
                  countries, number_different_countries, number_of_authors, emails)

        # Do not process the article if there is no information about the title, the authors or the abstract
        if h.is_empty(title) or h.is_empty(authors) or h.is_empty(abstract)\
                or len(abstract) <= Config.abstract_min_length:
            with lock:
                search.result_counts[MDPI_source][Config.PRISMA_parsing_errors] += 1
                search.parsing_errors_articles.append(fields)
            h.log_line('Skipping to process article for url:', url, 'because the data is incomplete.')
            return fields
        if h.is_empty(valid_doi):
            # This is a case when everything else was parsed successfully, but somehow the DOI wasn't correct,
            # which is not a critical issue
            with lock:
                search.parsing_errors_articles.append(fields)

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
