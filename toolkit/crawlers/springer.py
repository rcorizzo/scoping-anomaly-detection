import json
import os
import re
import threading
import urllib
from threading import Lock
import pandas as pd

from slugify import slugify

from configuration.config import *
from core.search_config import SearchConfig
from help_tools import helpers as h, hio
from help_tools.countries import Countries
from help_tools.helpers import is_email_valid
from help_tools.tools import tools


class Springer(object):
    # CONSTANTS
    url_template = 'https://link.springer.com/search/page/{0}?query={1}&date-facet-mode=between&facet-start-year={2}&facet-end-year={3}'
    absolute_uri = 'https://link.springer.com'

    @staticmethod
    def crawl(search: SearchConfig, lock: Lock = threading.Lock(), keyword: str = None):

        with lock:
            search.set_status('Springer', 'Starting')
            h.log_line('Crawling Springer...')
        if keyword:
            Springer._process_keyword(search, keyword, lock)
        else:
            for keyword in search.keywords:
                Springer._process_keyword(search, keyword, lock)
        with lock:
            search.set_status('Springer', value='Completed')
            search.to_pickle()

    @staticmethod
    def _process_keyword(search: SearchConfig, keyword: str, lock):
        links = Springer._crawl_keyword(search.folder_Springer_Links, keyword, search.start_year,
                                        search.end_year, search.folder_Springer_Data, search)
        dst_filename = os.path.join(search.folder_Springer_Links, slugify(keyword), slugify(keyword) + '_links.csv')

        with lock:
            search.set_result_counts(Config.sources['springer'])
        data = []
        for i, link in enumerate(links['link']):
            fields = Springer._scrape_article_page(search, link, lock, keyword)
            if fields:
                data.append(fields)
                if len(data) >= Config.max_papers_springer:
                    h.log_line('Breaking scraping articles for', Config.sources['springer'], 'because max papers:',
                               Config.max_papers_springer, 'was reached.', 'Total scraped articles:', len(data))
                    break
        with lock:
            search.write_results(data, dst_filename)

    @staticmethod
    def _crawl_keyword(folder_name, keyword, start_year, end_year, data_name, search):
        keyword_slug = slugify(keyword)
        keyword_folder = os.path.join(folder_name, keyword_slug)
        h.create_folder(keyword_folder)
        keyword_filename_template = os.path.join(keyword_folder, keyword_slug + '_page_{0}.txt')
        keyword_filename = os.path.join(keyword_folder, keyword_slug + '_urls_only.csv')
        data_folder = os.path.join(data_name)
        h.create_folder(data_folder)
        links = []
        if os.path.isfile(keyword_filename) and os.stat(keyword_filename).st_size > 0 and search.force_crawl is False:
            h.log_line('File exists:', keyword_filename, 'Skipping Springer download of', keyword)
            links = hio.pd_read_csv_or_excel(filename=keyword_filename, sep='\t', encoding='UTF-8')
            return links
        else:
            url_keyword = urllib.parse.quote_plus(keyword)

            data = []
            links = set()

            for year in range(search.start_year, search.end_year + 1):

                download_url = Springer.url_template.format("{0}", url_keyword, year, year)
                try:
                    # data = []
                    # links = set()
                    for page in range(1, Config.number_of_pages_springer + 1):
                        current_url = download_url.format(page)
                        web_page, current_url = tools.download_page(current_url, keyword_filename_template.format(page), search=search)
                        all_links_on_page = web_page.xpath('//a/@href')
                        article_links = Springer._filter_links(all_links_on_page, "/article/")
                        chapter_links = Springer._filter_links(all_links_on_page, "/chapter/")
                        new_links = article_links + chapter_links  # + reference_links + series
                        if len(all_links_on_page) == 0:
                            h.log_line('Breaking at page', page, 'because no new links were found.', 'Total links:', len(links))
                            break
                        for link in new_links:
                            if link not in links:
                                links.add(link)
                                data.append([page, link, current_url, keyword, Config.sources['springer']])
                        h.log_line('Page', page, 'of', Config.number_of_pages_springer, 'finished. Total links so far:',
                                   len(links))
                        if len(links) >= Config.max_papers_springer:
                            h.log_line('Breaking at page', page, 'because max papers:', Config.max_papers_springer,
                                       'was reached.', 'Total links:', len(links))
                            break
                except Exception as ex:
                    h.log_line(ex)
                    pass
            header = ['page', 'link', 'page_link', 'keyword', 'source']
            data = [header] + data
            h.write_csv_file(data, keyword_filename, separator='\t')

        # except Exception as ex:
        #     h.log_line(ex)
        #     pass
        df = pd.DataFrame(data[1:], columns=data[0])
        return df

    @staticmethod
    def _filter_links(all_links, relative_url):
        links = [Springer.absolute_uri + x for x in all_links if
                 relative_url in x and '.jpg' not in x and '.png' not in x and '.html' not in x and '.htm' not in x]
        return links

    _title_xpaths = ['//*[@id="book-header"]//h1[contains(@class,"app-journal-header__title")]/text()',
                     '//*[contains(@class, "app-journal-header__title")]/text()',
                     '//*[@id="main-content"]/main/article/header/div/h1/text()',
                     '//*[@class="c-article-title"]/text()',
                     '//*[@id="book-header"]/div/div[2]/div[1]/div[3]/h1/text()',
                     '//*[@id="kb-nav--main"]/div[1]/div/h1/text()',
                     '//*[@id="main-content"]/div/div/article/div/div[1]/div[2]/h1/text()',
                     '//*[@id="main-content"]/article/div/div/div/div[2]/div[1]/div[2]/h1/text()',
                     '//*[@id="main-content"]/article/div/div/div/div[1]/div[1]/div[2]/h1/text()',
                     '//*[@id="main-content"]/article/div/div/div/div[3]/div[1]/div[2]/h1/text()',
                     '//*[@id="book-header"]/div/div[2]/div[1]/div[3]/h1']

    _abstract_xpaths = ['//*[@id="Abs1-content"]/p/text()',
                        '//*[contains(@id, "about-this-book")]/../div/text()',  # not always okay
                        '//*[@id="Abs1"]/p/text()', '//*[@id="Par1"]/text()', '//*[@id="ASec1"]/p/text()',
                        '//*[@id="Sec1"]/div/p/text()', '//*[@id="body"]/p/text()', '//*[@id="Abs1_6"]/p/text()',
                        '//*[@id="Abs10"]/p/text()']

    _authors_xpaths = ['//*[@id="main-content"]//li[contains(@class,"c-article-author-list__item")]/a/text()',
                       '//*[@id="main-content"]/main/article/header/div/ul[1]/li/a/text()',
                       '//*[@id="main-content"]/main/section[7]/div/div/ul/li/p/text()',
                       '/html/body/div[2]/div[3]/main/section[7]/div/div/ul/li/p/text()',
                       '//*[@id="kb-nav--main"]/div[1]/ul/li/span/span[1]/text()',
                       '//*[@id="authors"]/ul/span[1]/text()',
                       '//*[@id="authorsandaffiliations"]/div/ul/li/span[1]/text()',
                       '//*[@id="authorsandaffiliations"]/div/ul/li/text()']
    # NO EMAILS FOUND ON PAGES
    _email_xpaths = ['//*[@id="authorsandaffiliations"]/div/ul/li[1]/span[2]/span[1]/a/@href',
                     '//*[@id="authorsandaffiliations"]/div/ul/li[1]/span[2]/span/a/@href']

    _affil_xpaths = ['//*[@id="main-content"]//h2[contains(@id, "affiliations")]/../div/ul/li/h3/text()',
                     '//*[@id="main-content"]//div[contains(@id, "author-information-content")]/ol/li/p[contains(@class, "c-article-author-affiliation__address")]/text()',
                     '//*[@id="main-content"]/main/section[7]/div/div/ul/li/h3/text()',
                     '//*[@id="author-information-content"]/ol/li/p[1]/text()',
                     '//*[@id="Aff16"]/p[1]/text()'
                     # '//*[@id="authorsandaffiliations"]/div',
                     '//*[@id="authorsandaffiliations"]/div/ol'
                     #                 '//*[@id="authorsandaffiliations"]/div/ol/li[3]'
                     ]

    _citations_xpaths = ['//*[@id="altmetric-container"]//ul/li[2]/p/text()',
                         '//*[@id="citations-count-number"]/text()',
                         '//*[@id="citations-link"]/span[1]/text()',
                         '//*[@id="chaptercitations-link"]/span[1]/text()',
                         '//*[@id="chaptercitations-count-number"]/text()',
                         '//*[@id="citations-count-number"]/span/text()']

    _date_xpaths = ['//*[@id="chapter-info-content"]/div/div/ul[2]/li[2]/p/span[2]/time/text()',
                    # no date on every link
                    '//*[@id="article-dates-history"]/div[2]/span[2]/time',
                    '//*[@class="c-bibliographic-information__list"]/li[1]/p/span[2]/time/text()',
                    '//*[@id="book-header"]/div/div[2]/div[1]/div[3]/ul/li[2]',
                    '//*[@id="enumeration"]/div/span[1]/time/text()',
                    '//*[@id="main-content"]/article/div/div/div/div[2]/div[1]/div[4]/div[1]/div/dl[1]/dd/time/text()',
                    '//*[@id="main-content"]/article/div/div/div/div[2]/div[1]/div[4]/div[1]/div/dl/dd/a/text()',
                    '//*[@id="main-content"]/article/div/div/div/div[3]/div[1]/div[4]/div[1]/div/dl/dd/a/text()',
                    '//*[@id="main-content"]/article/div/div/div/div[3]/div[1]/div[4]/div[1]/div/dl[1]/dd/time/text()',
                    '//*[@id="main-content"]/article/div/div/div/div[1]/div[1]/div[4]/div[1]/div/dl[1]/dd/time/text()',
                    '//*[@id="main-content"]/article/div/div/div/div[2]/div[1]/div[4]/div[1]/div/dl[0]/dd[0]/a/text()',
                    '//*[@class="gtm-first-online"]/text()'
                    '//*[@id="main-content"]/div/div/article/div/div[1]/div[4]/div[1]/div/div[1]/span[2]/a/text()'
                    ]

    _doi_xpaths = ['//*[@class="c-bibliographic-information__value"]/text()',
                   '//*[@id="chapter-info-content"]/div/div/ul[2]/li[1]/p/span[2]/text()',
                   '//*[@id="main-content"]/main/section[8]/div/div[1]/div/ul/li[5]/p/span[3]/text()',
                   '//*[@class="article-doi"]/p/text()',
                   '//*[@id="main-content"]/article/div/div/div/div[3]/div[1]/div[4]/div[1]/p/text()',
                   '//*[@id="main-content"]/article/div/div/div/div[2]/div[1]/div[4]/div[1]/p/text()',
                   '//*[@id="AboutThisContent"]/div/div[2]/ul[1]/li[1]/span[2]/text()',
                   '//*[@id="AboutThisContent"]/div/div/ul[1]/li[1]/span[2]/text()']

    _copyright_xpaths = ['//*[@id="main-content"]/main/section[8]/div/div[1]/div/ul/li[8]/p/span[3]/text()',
                         '//*[@id="copyright-information-content"]/p/text()',
                         '//*[@id="main-content"]/div/div/article/div/section[4]/div/div/text()',
                         '//*[@id="main-content"]/div/div/article/div/section[3]/div/div/text()']

    _publication_type_xpaths = [
        '//*[contains(@class,"c-article-info-details")]//a[contains(@data-test,"journal-link")]/descendant::*/text()',
        '//*[@id="main-content"]/main/section[8]/div/div[1]/div/ul/li[4]/p/span[3]/a/text()',
        '//*[@id="main-content"]/header/div/div/div[2]/div/div[3]/p[2]/a[1]/text()',
        '//*[@id="main-content"]/header/div/div/div[2]/div/div[3]/p/a/text()',
        '//*[@id="enumeration"]/p[1]/a/span/text()',
        '//div[contains(@class, "app-article-masthead")]//span[contains(@class, "app-article-masthead__journal-title")'
        ']/text()']

    _re_year_cite = re.compile(r'\((\d+)\)')

    @staticmethod
    def _scrape_article_page(search: SearchConfig, url, lock, keyword=None):
        SpringerSource = Config.sources['springer']
        filename = tools.html_filename(url, search.folder_Springer_Articles)
        data_filename = tools.json_filename(url, search.folder_Springer_Data)

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
            citations = data['number_of_citations']
            authors = data['authors']
            s_emails = data['emails']
            affiliations = data['affiliations']
            num_authors = data['number_of_authors']
            num_diff_affiliations = data['number_of_affiliations']
            countries = data['countries']
            num_diff_countries = data['number_of_countries']
            final_url = data['final_url']

            h.log_line(f'Springer data caching for article: {os.path.splitext(data_filename)[0]}')

        else:
            title = valid_doi = publication_title = date = year = abstract = citations = authors = s_emails = None
            affiliations = num_authors = num_diff_affiliations = countries = num_diff_countries = final_url = None
            try:
                web_page, final_url = tools.download_page(url, filename)
                title = None
                for xp in Springer._title_xpaths:
                    title = web_page.xpath(xp)
                    if title: break
                abstract = None
                for xp in Springer._abstract_xpaths:
                    abstract = web_page.xpath(xp)
                    if abstract: break

                authors = None
                for xp in Springer._authors_xpaths:
                    authors = web_page.xpath(xp)
                    if authors: break
                l_authors = []
                for _auth in authors:
                    s_auth = str(_auth)  # etree.tostring(_auth, pretty_print=True).decode('utf8')
                    s_auth = h.remove_tabs(s_auth.lstrip("0123456789. \t").replace(',', ' ').replace(';', ' '))
                    if not h.is_empty(s_auth):
                        l_authors.append(s_auth)
                authors = ','.join(l_authors)
                emails = []
                for xp in Springer._email_xpaths:
                    email = web_page.xpath(xp)
                    email = str(email).strip("[]'").replace('mailto:', '')
                    email = h.extract_email(email)
                    if is_email_valid(email):
                        emails.append(email)
                        break
                s_affil = None
                for xp in Springer._affil_xpaths:
                    s_affil = web_page.xpath(xp)
                    if s_affil: break

                s_affil = ';'.join(s_affil)
                affiliations, num_diff_affiliations, countries, num_diff_countries = Countries.process_affiliations(
                    s_affil)
                citations = None
                for xp in Springer._citations_xpaths:
                    citations = web_page.xpath(xp)
                    if citations: break

                date = None
                for xp in Springer._date_xpaths:
                    date = web_page.xpath(xp)
                    if date: break
                date = tools.clean_string(date)
                year = date[-4:] if date else ''
                if h.is_empty(year):
                    citeas = web_page.xpath('//*[@id="citethis-text"]/text()')
                    citeas = tools.clean_string(citeas)
                    if len(citeas) > 4:
                        yearm = Springer._re_year_cite.search(citeas)
                        if yearm:
                            year = yearm.group(1)
                            if h.is_empty(date):
                                date = year
                if h.is_empty(year):
                    _copyright = None
                    for xp in Springer._copyright_xpaths:
                        _copyright = web_page.xpath(xp)
                        if _copyright: break
                    _copyright = tools.clean_string(_copyright)
                    year = h.remove_non_numeric(_copyright)
                    if h.is_empty(date):
                        date = year

                doi = None
                for xp in Springer._doi_xpaths:
                    doi = web_page.xpath(xp)
                    if doi: break

                doi = tools.clean_string(doi).replace('https://doi.org/', '')
                valid_doi = tools.extract_doi(doi)
                publication_title = None
                for xp in Springer._publication_type_xpaths:
                    publication_title = web_page.xpath(xp)
                    if publication_title: break
                publication_title = tools.clean_string(publication_title)
                if h.is_empty(doi):
                    _doi = tools.simplify_url(final_url)
                    if len(_doi) > 0:
                        doi = _doi
                    else:
                        doi = h.remove_nonalpha(title, '')
                title = tools.clean_string(title)
                abstract = tools.clean_string(abstract)
                authors = tools.clean_string(authors).replace(';', ',')
                num_authors = authors.count(',') + 1
                citations = tools.clean_string(citations)
                if not citations or citations == '':
                    citations = 0

                if num_diff_countries > num_authors:
                    num_diff_countries = num_authors
                s_emails = ';'.join(emails)

                if not (authors or title or abstract or date or doi):
                    fields = None
                    return fields
            except Exception as ex:
                h.log_line('Error url', url, ex)
                if not keyword:
                    # we're testing, so re-raise the exception
                    raise ex
            finally:
                data_dict = {"title": title,
                             "doi": valid_doi,
                             "publication_title": publication_title,
                             "date": date,
                             "year": year,
                             "abstract": abstract,
                             "number_of_citations": citations,
                             "authors": authors,
                             "emails": s_emails,
                             "affiliations": affiliations,
                             "number_of_authors": num_authors,
                             "number_of_affiliations": num_diff_affiliations,
                             "countries": countries,
                             "number_of_countries": num_diff_countries,
                             "final_url": final_url,

                             }
                data_dict = json.dumps(data_dict)
                with open(data_filename, 'w', encoding='UTF-8') as fj:
                    fj.write(data_dict)
        fields = (
            valid_doi, final_url, title, authors, date, year, citations, abstract, keyword, SpringerSource,
            publication_title, affiliations, num_diff_affiliations, countries, num_diff_countries,
            num_authors, s_emails)
        if h.is_empty(authors) or h.is_empty(title) or h.is_empty(abstract) or len(
                abstract) < Config.abstract_min_length:
            with lock:
                search.result_counts[SpringerSource][Config.PRISMA_parsing_errors] += 1
                search.parsing_errors_articles.append(fields)
            return fields
        if h.is_empty(valid_doi):
            # This is a case when everything else was parsed successfully, but somehow the DOI wasn't correct,
            # which is not a critical issue
            with lock:
                search.parsing_errors_articles.append(fields)
        return fields
