import os.path
from threading import Thread, Lock

import matplotlib as mpl

from core.search_engine import process_articles
from crawlers.acm import ACM
from crawlers.elsevier import Elsevier
from crawlers.ieeexplore import IEEEXplore
from crawlers.mdpi import MDPI
from crawlers.ncbi_pubmed import PubMed
from crawlers.springer import Springer

from help_tools import helpers as h, hio
from core.search_config import SearchConfig
import time

from help_tools.browser_emulate import create_virtual_display
from help_tools.email_service import send_email_results

mpl.use('Agg')


def crawl_and_analyze(search: SearchConfig, file_manually_filtered_articles: str = None):
    lock = Lock()
    t0 = time.time()

    hio.archive_folder(search.folder_results)

    h.log_line('Starting ' + search.folder_data + '\n\n')
    crawlers = []
    if search.is_library_enabled("IEEE"):
        crawlers.append(IEEEXplore.crawl)
    if search.is_library_enabled("Springer"):
        crawlers.append(Springer.crawl)
    if search.is_library_enabled("MDPI"):
        crawlers.append(MDPI.crawl)
    if search.is_library_enabled('PubMed'):
        crawlers.append(PubMed.crawl)
    if search.is_library_enabled('Elsevier'):
        crawlers.append(Elsevier.crawl)
    if search.is_library_enabled('ACM'):
        crawlers.append(ACM.crawl)

    xvfb = create_virtual_display()
    try:
        threads = []
        if search.search_data["multithread"]:
            for crawler in crawlers:
                # instead of calling the function for each crawler we make a thread for each crawler,
                # with the corresponding function and the lock
                thread = Thread(target=crawler, args=(search, lock))
                threads.append(thread)

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        else:
            for crawler in crawlers:
                crawler(search)

    finally:
        xvfb.terminate()

    # process results
    process_articles(search, file_manually_filtered_articles=file_manually_filtered_articles)

    duration = time.time() - t0
    h.log_line('Finished. Duration:', duration)

    email_addresses = search.email_results
    search_name = os.path.basename(search.folder_data)
    h.log_line('Sending results to recipients:', email_addresses)
    send_email_results(email_addresses, search_name)
