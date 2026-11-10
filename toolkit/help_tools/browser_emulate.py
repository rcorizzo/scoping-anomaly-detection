import random
import subprocess
from typing import Any

import undetected_chromedriver as uc
from lxml.html import HtmlElement
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import time
import os
from help_tools import helpers as h
import glob
from configuration.config import Config
from help_tools.tools import tools
from lxml import html
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, TimeoutError


def create_chrome_browser(download_dir: str, enable_headless_download: bool = True):
    """
    Create a Chrome browser with default options

    :param download_dir: Path where to download the files
    :type download_dir: str
    :param enable_headless_download: Whether to enable headless browser download
    :type enable_headless_download: bool
    """
    user_agent = tools.get_stripped_useragent()

    patcher = uc.Patcher()
    patcher.auto()

    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--headless=new')
    options.add_argument('--nogui')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "download_restrictions": 0,
    }
    )

    service = Service(patcher.executable_path)
    # Adding user agent argument to avoid telling that this is headless chrome (It redirects if it is headless)
    options.add_argument(f'user-agent={user_agent}')
    browser = webdriver.Chrome(options=options, service=service)
    if enable_headless_download:
        enable_download_headless(browser, download_dir)

    return browser


def enable_download_headless(browser: WebDriver, download_dir: str):
    """
    There is currently a "feature" in chrome where headless browser does not allow file download:
    This method is a hacky work-around until the official chrome driver support for this.

    :param browser: The browser driver
    :type browser: WebDriver
    :param download_dir: Path where to download the files
    :type download_dir: str
    """
    browser.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
    params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
    browser.execute("send_command", params)

    return True


def create_firefox_browser(download_dir):
    options = webdriver.FirefoxOptions()
    options.headless = True
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", download_dir)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/x-gzip")

    driver = webdriver.Firefox(options=options, executable_path=GeckoDriverManager().install())
    return driver


def create_browser(download_dir):
    return create_firefox_browser(download_dir)
    # return create_chrome_browser(download_dir)


def download_file_selenium(url, download_dir, filename=None, wait_xpath='//body', return_string=False):
    if filename is None:
        filename = tools.html_filename(url)
    final_url = url
    if os.path.isfile(filename) and os.stat(filename).st_size > 0:
        h.log_line('File exists:', filename, 'Skipping download of', url)
        with open(filename, 'r', encoding="utf-8") as file:
            s = file.read()
    else:
        h.log_line('Downloading', url, 'to', filename)
        browser = create_browser(download_dir)
        browser.get(url)
        wait = WebDriverWait(browser, Config.browser_delay_time_acm)
        wait.until(EC.presence_of_element_located((By.XPATH, wait_xpath)))
        s = browser.page_source
        with open(filename, 'w+', encoding="utf-8") as f:
            f.write(s)
        browser.close()
    if return_string:
        web_page = s
    else:
        web_page = html.fromstring(s)
    return web_page, final_url


def download_ncbi_files(download_url, folder_name, filename, library_key):
    h.log_line(download_url, 'download', filename)
    status = True
    if os.path.isfile(filename) and os.stat(filename).st_size > 0:
        h.log_line('File', filename, 'exists. Size (MB):', round(os.stat(filename).st_size / 10 ** 6, 2),
                   'Skipping download.')
        return status
    search_form_filename = tools.html_filename(download_url, folder_name)
    search_form_result = tools.download_file_simple(download_url, search_form_filename)
    if 'No documents match your search terms' in search_form_result:  # r.text:
        h.log_line('No documents match the search term:', download_url)
        return False
    browser = create_browser(download_dir=folder_name)
    browser.get(download_url)
    wait = WebDriverWait(browser, Config.max_download_time_selenium)
    try:
        downloaded_file = os.path.join(folder_name, library_key + "_result.xml")
        if os.path.isfile(downloaded_file):
            os.remove(downloaded_file)
        elmSendTo = wait.until(EC.presence_of_element_located((By.ID, 'sendto')))
        elmSendTo.click()

        elmFileRadio = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@id='dest_File'][@type='radio']")))
        elmFileRadio.click()

        elmSelectXML = wait.until(EC.visibility_of_element_located(
            (By.XPATH,
             "//div[@id='send_to_menu']/div[@id='submenu_File']/ul/li/select[@id='file_format']/option[@value='xml']")))
        elmSelectXML.click()

        elmBtnCreateFile = wait.until(EC.visibility_of_element_located(
            (By.XPATH,
             "//div[@id='send_to_menu']/div[@id='submenu_File']/button[@type='submit'][@cmd='File']")))
        elmBtnCreateFile.click()
        slept = 0
        sleep_increment = 5
        prev_size = 0
        downloaded_file_part = downloaded_file + '.part'
        while True:
            h.log_line('Waiting for download to finish of:', downloaded_file, 'Elapsed time:', slept)
            time.sleep(sleep_increment)
            while os.path.isfile(downloaded_file_part) and os.stat(downloaded_file_part).st_size > 0:
                cur_size = os.stat(downloaded_file_part).st_size
                if cur_size > prev_size:
                    h.log_line('Elapsed:', slept, 'Sleeping while downloading:', filename, ':', downloaded_file_part,
                               'Size (MB) increased from:', prev_size * 1.0 / 10 ** 6,
                               'to', cur_size * 1.0 / 10 ** 6)
                    prev_size = cur_size
                    time.sleep(sleep_increment)
                    slept += sleep_increment
                else:
                    break

            if os.path.isfile(downloaded_file):
                h.log_line('It seems the result is downloaded to:', downloaded_file, 'Size (MB):',
                           os.stat(downloaded_file).st_size // 10 ** 6)
                break
            if slept > Config.max_download_time_selenium:
                h.log_line('Interrupting download of:', downloaded_file, 'after:', slept)
                break
            slept += sleep_increment
        if not os.path.exists(downloaded_file):
            h.log_line("File wasn't downloaded to:", downloaded_file, 'Stopping after:', slept, 'seconds.')
        else:
            os.rename(downloaded_file, filename)
    except Exception as e:
        h.log_line('Failed for:', download_url, e)
        h.write_csv_file(None, filename)
        status = False
    time.sleep(5)
    browser.close()
    return status


def download_ieeexplore_files(download_url, folder_name, filename):
    h.log_line(download_url, 'download', filename)
    status = True
    if os.path.isfile(filename) and os.stat(filename).st_size > 0:
        h.log_line('File', filename, 'exists. Size (MB):', round(os.stat(filename).st_size / 10 ** 6, 2),
                   'Skipping download.')
        return status
    search_form_filename = tools.html_filename(download_url, folder_name)
    search_form_result = tools.download_file_simple(download_url, search_form_filename)
    if 'No documents match your search terms' in search_form_result:  # r.text:
        h.log_line('No documents match the search term:', download_url)
        return False
    browser = create_browser(download_dir=folder_name)
    browser.get(download_url)
    wait = WebDriverWait(browser, Config.max_download_time_selenium)
    try:
        downloaded_file = os.path.join(folder_name, "result.xml")
        if os.path.isfile(downloaded_file):
            os.remove(downloaded_file)
        elmSendTo = wait.until(EC.presence_of_element_located((By.ID, 'sendto')))
        elmSendTo.click()

        elmFileRadio = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@id='dest_File'][@type='radio']")))
        elmFileRadio.click()

        elmSelectXML = wait.until(EC.visibility_of_element_located(
            (By.XPATH,
             "//div[@id='send_to_menu']/div[@id='submenu_File']/ul/li/select[@id='file_format']/option[@value='xml']")))
        elmSelectXML.click()

        elmBtnCreateFile = wait.until(EC.visibility_of_element_located(
            (By.XPATH,
             "//div[@id='send_to_menu']/div[@id='submenu_File']/button[@type='submit'][@cmd='File']")))
        elmBtnCreateFile.click()
        slept = 0
        sleep_increment = 5
        prev_size = 0
        downloaded_file_part = downloaded_file + '.part'
        while True:
            h.log_line('Waiting for download to finish of:', downloaded_file, 'Elapsed time:', slept)
            time.sleep(sleep_increment)
            while os.path.isfile(downloaded_file_part) and os.stat(downloaded_file_part).st_size > 0:
                cur_size = os.stat(downloaded_file_part).st_size
                if cur_size > prev_size:
                    h.log_line('Elapsed:', slept, 'Sleeping while downloading:', filename, ':', downloaded_file_part,
                               'Size (MB) increased from:', prev_size * 1.0 / 10 ** 6,
                               'to', cur_size * 1.0 / 10 ** 6)
                    prev_size = cur_size
                    time.sleep(sleep_increment)
                    slept += sleep_increment
                else:
                    break

            if os.path.isfile(downloaded_file):
                h.log_line('It seems the result is downloaded to:', downloaded_file, 'Size (MB):',
                           os.stat(downloaded_file).st_size // 10 ** 6)
                break
            if slept > Config.max_download_time_selenium:
                h.log_line('Interrupting download of:', downloaded_file, 'after:', slept)
                break
            slept += sleep_increment
        if not os.path.exists(downloaded_file):
            h.log_line("File wasn't downloaded to:", downloaded_file, 'Stopping after:', slept, 'seconds.')
        else:
            os.rename(downloaded_file, filename)
    except Exception as e:
        h.log_line('Failed for:', download_url, e)
        h.write_csv_file(None, filename)
        status = False
    time.sleep(5)
    browser.close()
    return status


def download_acm_files(download_url, folder_name_temp, filename_bib, filename_csv):
    h.log_line(download_url, 'download', filename_bib, filename_csv)
    status = True
    if os.path.isfile(filename_bib) and os.path.isfile(filename_csv) and os.stat(filename_bib).st_size > 0 and os.stat(
            filename_csv).st_size > 0:
        h.log_line('Files', filename_bib, filename_csv, 'exist. Skipping download.')
        return status
    browser = create_browser(download_dir=folder_name_temp)

    browser.get(download_url)
    wait = WebDriverWait(browser, Config.browser_delay_time_acm)
    try:
        # '//*[@id="searchtools"]/a[1]'
        elmBibtex = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="searchtools"]/a[1]')))
        # <a href="exportformats_search.cfm?query=%28dominik%20slezak%29&amp;filtered=&amp
        # ;within=owners%2Eowner%3DHOSTED&amp;dte=2008&amp;bfr=2018&amp;srt=%5Fscore&amp;expformat=csv">csv</a>
        # https://dl.acm.org/exportformats_search.cfm?query=%28dominik%20slezak%29&filtered=&within=owners%2Eowner%3DHOSTED&dte=2008&bfr=2018&srt=%5Fscore&expformat=csv
        elmBibtex.click()
        # '//*[@id="searchtools"]/a[4]'
        elmCSV = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="searchtools"]/a[4]')))
        elmCSV.click()
        while True:
            bib_files = glob.glob(os.path.join(folder_name_temp, '*.bib'))
            if len(bib_files) > 0:
                last_bib_file = max(bib_files, key=os.path.getctime)
                os.rename(last_bib_file, filename_bib)
                break
            time.sleep(1)
        while True:
            csv_files = glob.glob(os.path.join(folder_name_temp, '*.csv'))
            if len(csv_files) > 0:
                last_csv_file = max(csv_files, key=os.path.getctime)
                os.rename(last_csv_file, filename_csv)
                break
            time.sleep(1)
    except Exception as e:
        h.log_line('Failed for:', download_url, e)
        h.write_csv_file(None, filename_bib)
        h.write_csv_file(None, filename_csv)
        status = False
    time.sleep(5)
    browser.close()
    return status


def cookie_to_txt(c: dict):
    """domain - The domain that created AND that can read the variable.
flag - A TRUE/FALSE value indicating if all machines within a given domain can access the variable.
 This value is set automatically by the browser, depending on the value you set for domain.
path - The path within the domain that the variable is valid for.
secure - A TRUE/FALSE value indicating if a secure connection with the domain is needed to access the variable.
expiration - The UNIX time that the variable will expire on.
UNIX time is defined as the number of seconds since Jan 1, 1970 00:00:00 GMT.
name - The name of the variable.
value - The value of the variable."""
    try:
        ll = [c['domain'], str(c['domain'][0] == '.'), c['path'], c['secure'], c['expiry'], c['name'], c['value']]
        t = h.list_to_str(ll, separator='\t')
        return t
    except Exception as e:
        h.log_line('Cookie not converted!', c, e)
        return ''


def download_acm_files_test(
        download_url='https://dl.acm.org/results.cfm?query=(dominik%20slezak)'
                     '&within=owners.owner=HOSTED&filtered=&dte=2008&bfr=2018',
        folder_name_temp='/home/eftim/article-analysis/data/AAL_20180921/acm/temp',
        filename_bib='/home/eftim/article-analysis/data/AAL_20180921/acm/dominik-slezak.bib',
        filename_csv='/home/eftim/article-analysis/data/AAL_20180921/acm/dominik-slezak.csv'):
    start_year = 2008
    end_year = 2018
    url_keyword = 'dominik%20slezak'
    url_template_download = 'http://dl.acm.org/exportformats_search.cfm?query={0}&' \
                            'filtered=&within=owners%2Eowner%3DHOSTED&dte={1}&bfr={2}&srt=%5Fscore&expformat={3}'

    download_url_bib = url_template_download.format(url_keyword, start_year, end_year, 'bibtex')
    download_url_csv = url_template_download.format(url_keyword, start_year, end_year, 'csv')

    # tools.tools.download_file_simple(download_url_bib,filename_bib)
    # tools.tools.download_file_simple(download_url_csv, filename_csv)

    # THROWS error
    # tools.tools.download_file_simple2(download_url_bib,filename_bib)
    # tools.tools.download_file_simple2(download_url_csv, filename_csv)
    # tools.tools.download_file_wget(download_url_bib,filename_bib)
    # tools.tools.download_file_wget(download_url_csv, filename_csv)
    # return
    h.log_line(download_url, 'download', filename_bib, filename_csv)
    status = True
    if os.path.isfile(filename_bib) and os.path.isfile(filename_csv) and os.stat(filename_bib).st_size > 0 and os.stat(
            filename_csv).st_size > 0:
        h.log_line('Files', filename_bib, filename_csv, 'exist. Skipping download.')
        return status
    browser = create_browser(download_dir=folder_name_temp)
    browser.get(download_url)
    wait = WebDriverWait(browser, Config.browser_delay_time_acm)
    cookies_txt = [cookie_to_txt(c) for c in browser.get_cookies()]
    cookies_filename = os.path.join(folder_name_temp, 'cookies.txt')
    h.write_csv_file(cookies_txt, cookies_filename)

    args = ['wget', '--cookies=on', '--load-cookies', cookies_filename, '-o', filename_bib + '.log', '-O', filename_bib,
            download_url_bib]
    cmd = ' '.join(args)
    # h.safe_exec_bash_cmd(args)
    print(cmd)
    args = ['wget', '--cookies=on', '--load-cookies', cookies_filename, '-o', filename_bib + '.log', '-O', filename_csv,
            download_url_csv]
    # h.safe_exec_bash_cmd(args)
    cmd = ' '.join(args)
    print(cmd)
    # return
    try:
        # elmBibtex = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='searchtools']/a[1]")))
        elmBibtex = wait.until(EC.visibility_of_element_located((By.PARTIAL_LINK_TEXT, "bibtex")))
        elmBibtex.click()
        while True:
            bib_files = glob.glob(os.path.join(folder_name_temp, '*.bib'))
            if len(bib_files) > 0:
                last_bib_file = max(bib_files, key=os.path.getctime)
                os.rename(last_bib_file, filename_bib)
                break
            time.sleep(1)
        # # elmCSV = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='searchtools']/a[4]")))
        elmCSV = wait.until(EC.visibility_of_element_located((By.PARTIAL_LINK_TEXT, "csv")))
        elmCSV.click()
        while True:
            csv_files = glob.glob(os.path.join(folder_name_temp, '*.csv'))
            if len(csv_files) > 0:
                last_csv_file = max(csv_files, key=os.path.getctime)
                os.rename(last_csv_file, filename_csv)
                break
            time.sleep(1)
    except Exception as e:
        h.log_line('Failed for:', download_url, e)
        h.write_csv_file(None, filename_bib)
        h.write_csv_file(None, filename_csv)
        status = False
    finally:
        time.sleep(5)
        browser.close()
    return status


def extract_links(url, browser, wait):
    links = set()
    browser.get(url)
    wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")

    try:
        browser.refresh()

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'List-results-items')))

        divs = browser.find_elements(By.CLASS_NAME, 'List-results-items')

        for div in divs:
            try:
                h3_tags = div.find_elements(By.TAG_NAME, 'h3')
                for h3 in h3_tags:
                    a_tag = h3.find_element(By.TAG_NAME, 'a')
                    if a_tag:
                        links.add(a_tag.get_attribute('href'))
            except NoSuchElementException:
                pass

    except (TimeoutException, NoSuchElementException):
        browser.save_screenshot(f"missing_{url.replace('/', '_')}.png")
        return links

    return links

def create_virtual_display():
    # start virtual display for browser to spoof bot detection
    xvfb = subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1920x1080x24"])
    os.environ['DISPLAY'] = ':99'

    return xvfb

def terminate_virtual_display(xvfb: subprocess.Popen):
    xvfb.terminate()

class PlaywrightBrowser:
    def __init__(self,
                 browser,
                 context,
                 page: Page):
        self.browser: Browser = browser
        self.context: BrowserContext = context
        self.page: Page = page

    def rotate_context(self):
        self.context.close()
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

def create_playwright_browser(playwright):
    browser = playwright.chromium.launch(
        headless=False,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-setuid-sandbox',
            '--disable-infobars',
            '--window-position=0,0',
            '--ignore-certificate-errors',
            '--ignore-ssl-errors',
        ]
    )
    context = browser.new_context(
        viewport={"width": 1366, "height": 768},
    )
    page = context.new_page()

    return PlaywrightBrowser(browser, context, page)


def download_links(url: str, exported_file_name: str, source: str):
    """
    Export CSV data by providing url with query string parameters and the source

    :param url: The url query
    :type url: str
    :param exported_file_name: Where to export the file
    :type exported_file_name: str
    :param source: The source for which the links should be downloaded (to know which function to call)
    :type source: str

    :return: Whether the download was successful
    :rtype: bool
    """

    # write into log file
    h.log_line(f'Starting to download the file:', url, 'into:', exported_file_name)

    # create a Chrome browser
    download_directory = os.path.dirname(exported_file_name)
    browser = create_chrome_browser(download_dir=download_directory)

    wait_time_to_download = 0
    t_start = int(time.time())
    try:

        if source == 'ieee':
            wait_time_to_download = _download_links_ieee(browser, url)
        elif source == 'pubmed':
            wait_time_to_download = _download_links_pubmed(browser, url)
        else:
            raise Exception(f'The provided source: {source} is not acceptable.')

        # Wait for the file to be downloaded and rename it to previously provided file name
        elapsed_time = 0
        while elapsed_time <= wait_time_to_download:
            if elapsed_time < 10 or elapsed_time % 5 == 0:
                h.log_line('Waiting for download to finish for:', exported_file_name, 'Elapsed time:',
                           elapsed_time, 'seconds')
            elapsed_time += 1

            csv_files = glob.glob(os.path.join(download_directory, '*.csv'))  # get all csv files in a folder
            if len(csv_files) > 0:
                last_csv_file = max(csv_files, key=os.path.getmtime)  # get the last csv file
                if int(os.path.getmtime(last_csv_file)) > t_start:  # if the last file is modified after the start time
                    if os.path.exists(exported_file_name):
                        os.remove(exported_file_name)
                    os.rename(last_csv_file, exported_file_name)  # rename the file
                    h.log_line(f'Finished downloading the file:', url, 'into:', exported_file_name)
                    return True

            time.sleep(1)

    except WebDriverException as wde:
        h.log_line('Web driver exception:', wde)
        h.log_line(f'Failed to download the file:', url)
    except Exception as ex:
        h.log_line('Exception:', ex)
        h.log_line(f'Failed to download the file:', url)
    finally:
        browser.close()

    h.log_line(f'Failed to download the file:', url, 'Time spent:', wait_time_to_download, 'seconds.')
    return False


def _download_links_ieee(browser: WebDriver, url: str) -> int:
    """
    Download links in CSV format for IEEE database.

    :param browser: Selenium WebDriver
    :type browser: webdriver
    :param url: The url query
    :type url: str

    :return: Maximum waiting time for download
    :rtype: int
    """

    # Crawl IEEE for a specific keyword
    browser.get(url)
    wait = WebDriverWait(browser, timeout=Config.browser_delay_time_ieee)

    # Find the export button and click it
    export_button_xpath = '//*[@id="xplMainContent"]//xpl-export-search-results/button'
    export_button = wait.until(EC.element_to_be_clickable((By.XPATH, export_button_xpath)))
    export_button.click()

    # Find the download button inside the export window and click it
    download_button_xpath = '//div[contains(@id, "ngb-nav-2-panel")]//button[2]'
    download_button = wait.until(EC.element_to_be_clickable((By.XPATH, download_button_xpath)))
    download_button.click()

    return Config.max_download_time_selenium_ieee


def _download_links_pubmed(browser: WebDriver, url: str) -> int:
    """
    Download links in CSV format for PubMed database.

    :param browser: Selenium WebDriver
    :type browser: webdriver
    :param url: The url query
    :type url: str

    :return: Maximum waiting time for download
    :rtype: int
    """

    # Crawl Pubmed for a specific keyword
    browser.get(url)
    wait = WebDriverWait(browser, timeout=Config.browser_delay_time_pubmed)

    # Find the save button and click it
    save_button_id = 'save-results-panel-trigger'
    save_button = wait.until(EC.element_to_be_clickable((By.ID, save_button_id)))
    save_button.click()

    # Find the save selection dropdown field and choose all results to be saved
    save_selection_id = 'save-action-selection'
    save_selection = wait.until(EC.element_to_be_clickable((By.ID, save_selection_id)))
    save_selection_option = Select(save_selection)
    save_selection_option_value = 'all-results'
    save_selection_option.select_by_value(save_selection_option_value)

    # Find the save format dropdown field and choose all results to be saved
    save_format_id = 'save-action-format'
    save_format = wait.until(EC.element_to_be_clickable((By.ID, save_format_id)))
    save_format_option = Select(save_format)
    save_format_option_value = 'csv'
    save_format_option.select_by_value(save_format_option_value)

    # Find the create file button inside the save window and click it
    create_file_button_xpath = '//*[@id="save-action-panel-form"]//button[contains(@class, "action-panel-submit")]'
    create_file_button = wait.until(EC.element_to_be_clickable((By.XPATH, create_file_button_xpath)))
    create_file_button.click()

    return Config.max_download_time_selenium_pubmed


def download_page_elsevier(pw:PlaywrightBrowser, url: str, filename: str, search):
    """
    Download search page for Elsevier database

    :param browser: Chrome browser
    :type browser: webdriver.Chrome
    :param url: The url we want to download
    :type url: str
    :param filename: Filename where to store the page
    :type filename: str
    :param search: Access to search object

    :return: The web page as HTML element and the new url if there is redirecting
    :rtype: Tuple[HTMLElement, str]
    """

    content_id = 'srp-results-list'
    if os.path.isfile(filename) and os.stat(filename).st_size > 0 and search.force_crawl is False:
        h.log_line('File exists:', filename, 'Skipping download of', url)
        content_html = h.read_file(filename)
    else:
        h.log_line('Downloading', url, 'to', filename)
        content_html = None
        try:
            # Import Elsevier class here to avoid circular imports
            from crawlers.elsevier import Elsevier

            # Use the exponential backoff method
            if Elsevier.request_with_backoff(pw, url):
                content = pw.page.locator(f"css=#{content_id}").nth(0).inner_html()

        except TimeoutException as wde:
            h.log_line('Timeout exception:', wde)
            h.log_line(f'Failed to download the file:', url)
        except Exception as ex:
            h.log_line('Exception:', ex)
            h.log_line(f'Failed to download the file:', url)
        finally:
            if content_html is None:
                content_html = pw.page.locator("css=#main_content").nth(0).inner_html()
            with open(filename, 'w', encoding='utf-8') as fout:
                fout.write(content_html)

    web_page = html.fromstring(content_html)
    return web_page, url

def download_page_acm(
        pw: PlaywrightBrowser,
        url: str,
        filename: str,
        search,
        attempt: int = 1,
        wait_until: str = 'domcontentloaded',
        timeout: int = None,
        is_article_page: bool = False,
) -> tuple[None, str] | tuple[HtmlElement, str] | tuple[Any, str]:

    from crawlers.acm import ACM
    if os.path.isfile(filename) and os.stat(filename).st_size > 0 and search.force_crawl is False:
        h.log_line('File exists:', filename, 'Skipping download of', url)
        content_html = h.read_file(filename)
        web_page = html.fromstring(content_html)
    else:
        h.log_line('Downloading', url, 'to', filename)
        content_html = None
        try:
            base_delay = random.uniform(ACM.random_delay_min, ACM.random_delay_max)
            delay = base_delay * (ACM.backoff_factor ** (attempt - 1))

            h.log_line(f"Request attempt {attempt} for {url}. Waiting {delay:.2f} seconds...")
            time.sleep(delay)

            # If timeout is not provided, use the config default
            if timeout is None:
                timeout = Config.browser_delay_time_acm * 1000

            res = pw.page.goto(url, wait_until=wait_until, timeout=timeout)
            if res.status != 200:
                raise Exception(f"Request failed with status code {res.status}")
            if is_article_page:
                try:
                    pw.page.locator(f'xpath={ACM.AUTHORS_PANE_BUTTON_XPATH}').click(timeout=5000)
                    pw.page.wait_for_selector(ACM.AUTHORS_PANE_CONTAINER_XPATH, timeout=5000)
                except TimeoutError as e:
                    h.log_line(f"Timeout error while clicking on the authors pane button: {e}")

            content_html = pw.page.content()
            web_page = html.fromstring(content_html)

        except TimeoutError as wde:
            h.log_line('Timeout exception:', wde)
            h.log_line(f'Failed to download the file:', url)
            return None, url
        except Exception as e:
            h.log_line("Rotating context because of rate limit")
            pw.rotate_context()
            if attempt < ACM.max_attempts:
                h.log_line(f"Retrying... (Attempt {attempt + 1} of {ACM.max_attempts})")
                return download_page_acm(pw, url, filename, search, attempt + 1, wait_until, timeout)
            else:
                h.log_line(f"Max attempts ({ACM.max_attempts}) reached. Giving up on: {url}")
                return None, url
        finally:
            with open(filename, 'w', encoding='utf-8') as fout:
                fout.write(content_html)

    # web_page = html.fromstring(content_html)
    return web_page, url
