from math import ceil


class Config(object):
    # CONFIGURATION
    min_properties_relevant = 3
    max_papers_springer = 5000
    max_papers_acm = 5000
    max_papers_mdpi = 5000
    max_papers_elsevier = 5000
    max_papers_pubmed = 5000
    max_papers_ieee = 2000

    max_article_authors = 100
    max_article_affiliations = 35
    number_of_synonyms_word_phrase = 3
    number_of_pages_springer = ceil(max_papers_springer / 10)
    number_of_pages_acm = ceil(max_papers_acm / 20)
    number_of_pages_mdpi = ceil(max_papers_mdpi / 10)  # Page count = 15 in MDPI URI TEMPLATE
    number_of_pages_elsevier = 10  # Maximum 10 pages are available
    number_of_pages_ieee = ceil(max_papers_ieee / 100)

    browser_delay_time_acm = 60  # Selenium - time for browser to load dynamic content
    browser_delay_time_ncbi = 60  # Selenium - time for browser to load dynamic content
    browser_delay_time_ieee = 60  # Selenium - time for browser to load dynamic content
    browser_delay_time_pubmed = 60  # Selenium - time for browser to load dynamic content
    browser_delay_time_elsevier = 20  # Selenium - time for browser to load dynamic content

    max_download_time_selenium = 2 * 3600  # seconds
    max_download_time_selenium_ieee = 2 * 60  # 10 minutes by 60 seconds
    max_download_time_selenium_pubmed = 10 * 60  # 10 minutes by 60 seconds

    abstract_min_length = 10
    abstract_export_max_length = 3000

    DATA_FOLDER = 'data'
    ACM_FOLDER = 'acm'
    NCBI_FOLDER = 'ncbi'
    SPRINGER_FOLDER = 'springer'
    IEEEXPLORE_FOLDER = 'ieeexplore'
    MDPI_FOLDER = 'mdpi'
    PUBMED_FOLDER = 'pubmed'
    ELSEVIER_FOLDER = 'elsevier'
    # CONSTANTS
    sources = {'springer': 'Springer', 'acm': 'ACM', 'ieee': 'IEEE Xplore', 'ncbi': 'NCBI', 'pubmed': 'NCBI:PubMed',
               'mdpi': 'MDPI', 'elsevier': 'Elsevier'}
    valid_sources = ['NCBI:PubMed', 'Springer', 'ACM', 'IEEE Xplore', 'MDPI', 'Elsevier']

    PRISMA_parsing_errors = 'parsing_errors'
    PRISMA_considered = 'considered'
    PRISMA_invalid_years = 'invalid_years'
    PRISMA_incomplete_data = 'incomplete_data'
    PRISMA_duplicates = 'duplicates'
    PRISMA_remaining = 'remaining'
    PRISMA_relevant = 'relevant'
    PRISMA_selected = 'selected'
    PRISMA_search_stats_header = [PRISMA_parsing_errors, PRISMA_considered, PRISMA_invalid_years,
                                  PRISMA_incomplete_data,
                                  PRISMA_duplicates, PRISMA_remaining, PRISMA_relevant, PRISMA_selected]

    keywords_result_header = ['doi', 'link', 'title', 'authors', 'date', 'year', 'citations',
                              'abstract', 'keyword', 'source', 'publication_title', 'affiliations',
                              'num_diff_affiliations', 'countries', 'num_diff_countries', 'num_authors', 'emails']
    keywords_result_header_extended = keywords_result_header + ['abstract_stemmed', 'bibtex_id']
    keywords_summary_header = keywords_result_header + ['bibtex_id', 'num_property_groups', 'num_properties',
                                                        'all_keywords', 'all_sources',
                                                        'is_article_relevant', 'Included', 'Comment', 'property_groups', 'properties']
