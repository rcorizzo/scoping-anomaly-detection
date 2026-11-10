import glob
import hashlib
import json
import os
import random
import re
import shutil
import urllib
from itertools import permutations
from random import randint
from threading import Timer
from urllib.request import urlretrieve

import nltk
import nltk.data
import numpy as np
import requests
import wget
from lxml import html
from nltk.corpus import stopwords
from nltk.corpus import wordnet
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import sent_tokenize, word_tokenize
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from slugify import slugify
import undetected_chromedriver as uc

from configuration.config import Config
from help_tools import helpers as h

# from browser_emulate import download_file_selenium

lemmatizer = WordNetLemmatizer()
stemmer = PorterStemmer()


class tools(object):
    stop_words = set(stopwords.words('english'))
    re_doi = re.compile(r"\b(10[.][0-9]{4,}(?:[.][0-9]+)*/(?:(?![\"&\'])\S)+)\b")

    @staticmethod
    def extract_doi(doi_string: str):
        if not doi_string:
            return ""
        matches = tools.re_doi.findall(doi_string)
        if len(matches) == 0:
            return ""
        else:
            return matches[0]

    @staticmethod
    def get_stripped_useragent():
        """
        Returns a current user-agent from a temporary webdriver, but stripped of the word "Headless".
        """
        return  'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'

    @staticmethod
    def is_subsequence(a, b):
        """Returns true if a is a subsequence of b.
        e.g. (2,3,4,2) is a subsequence of (1,2,3,4,2,5) but not of (2,3,4)"""
        if a is None and b is None:
            return True
        if a is None:
            return False
        if b is None:
            return False
        if type(a) != type(b):
            return False
        if type(a) not in (list, tuple, str) or type(b) not in (list, tuple, str):
            return False
        ln1 = len(a)
        ln2 = len(b)
        if ln1 == 0 or ln2 == 0:
            return False
        if ln1 == ln2:
            return a == b
        elif ln1 < ln2:
            l1 = a
            l2 = b
        else:
            l1 = b
            l2 = a
        return tools.__sublist(l1, l2)

    @staticmethod
    def __sublist(sublist, lst):
        sublist_len = len(sublist)
        k = 0
        s = None

        if sublist_len > len(lst):
            return False
        elif sublist_len == 0:
            return True

        for x in lst:
            if x == sublist[k]:
                if k == 0:
                    s = x
                elif x != s:
                    s = None
                k += 1
                if k == sublist_len:
                    return True
            elif k > 0 and sublist[k - 1] != s:
                k = 0
        return False

    @staticmethod
    def lin_coef(y, x=None):
        try:
            if not x:
                # x = np.arange(0, len(y))
                # x = np.linspace(y[0], y[-1], len(y))
                x = np.linspace(min(y), max(y), len(y))
            c = np.polyfit(x, np.array(y), 1)
            if np.isnan(c[0]):
                a = 0
            else:
                a = round(c[0], 2)
            return a
        except:
            return 0

    @staticmethod
    def add_lin_coef_to_df_name(df):
        for col in df.columns:
            if col != 'year':
                values = df[col].tolist()
                lin_c = tools.lin_coef(values[:-1])
                lin_c5 = tools.lin_coef(values[-6:-1])
                df.rename({col: col.replace('_', ' ') + ' (%s/%s)' % (lin_c, lin_c5)}, axis='columns', inplace=True)

    @staticmethod
    def between(value, a, b):
        """
        Return the string between a and b
        :param value:
        :param a:
        :param b:
        :return:
        """
        #
        if isinstance(value, bytes):
            value = value.decode('utf8')
            h.log_line('Converting from bytes to str')
        try:
            pos_a = value.find(a)
        except Exception as e:
            h.log_line('Exception type 1:find', e, 'type(a), a, type(value), value', type(a), a, type(value), value)
            raise e
        if pos_a == -1: return ""
        try:
            value = value[pos_a + len(a):]
        except Exception as e:
            h.log_line('Exception type 2:cut', e, 'pos_a, len(a)', pos_a, len(a))
            raise e
        try:
            pos_b = value.find(b)
        except Exception as e:
            h.log_line('Exception type 3:find', e, 'type(b), b, type(value), value', type(b), b, type(value), value)
            raise e
        if pos_b == -1: return ""
        return value[:pos_b]

    @staticmethod
    def before(value, a):
        """
        Find first part and return slice before it.
        :param value:
        :param a:
        :return:
        """
        pos_a = value.find(a)
        if pos_a == -1: return ""
        return value[0:pos_a]

    @staticmethod
    def get_synonyms(keyphase):
        keyphase = keyphase.lower()
        synonyms = tools.get_synonyms_single_word(keyphase)
        if ' ' in keyphase:
            for i in range(Config.number_of_synonyms_word_phrase):
                synonyms.append(tools.get_synonym_for_word_phrase(keyphase))
        synonyms = sorted(set(synonyms))
        return synonyms

    @staticmethod
    def get_synonyms_single_word(word):
        synonyms = []
        for syn in wordnet.synsets(word):
            for l in syn.lemmas():
                synonyms.append(str(l.name()).replace('_', ' '))
        return synonyms

    @staticmethod
    def get_synonym_for_word_phrase(word_phrase):
        synonym = ""
        # Tokenize the text
        # Get the list of words from the entire text
        words = word_tokenize(word_phrase)
        # Identify the parts of speech
        tagged = nltk.pos_tag(words)

        for i in range(len(words)):
            replacements = []
            # Only replace nouns with nouns, vowels with vowels etc.
            for syn in wordnet.synsets(words[i]):
                # Do not attempt to replace proper nouns or determiners
                if tagged[i][1] == 'NNP' or tagged[i][1] == 'DT':
                    break
                # The tokenizer returns strings like NNP, VBP etc
                # but the wordnet synonyms has tags like .n.
                # So we extract the first character from NNP ie n
                # then we check if the dictionary word has a .n. or not
                word_type = tagged[i][1][0].lower()
                if syn.name().find("." + word_type + "."):
                    # extract the word only
                    r = syn.name()[0:syn.name().find(".")]
                    replacements.append(r.replace('_', ' '))

            if len(replacements) > 0:
                # Choose a random replacement
                replacements = list(set(replacements))
                replacement = replacements[randint(0, len(replacements) - 1)]
                synonym += " " + replacement
            else:
                # If no replacement could be found, then just use the
                # original word
                synonym += " " + words[i]
        return synonym.lstrip().lower()

    @staticmethod
    def get_lemma(word):
        return lemmatizer.lemmatize(word)

    @staticmethod
    def get_stem(word):
        return stemmer.stem(word)

    @staticmethod
    def remove_stopwords(sentence):
        filtered_words = [w for w in sentence if w not in tools.stop_words]
        return filtered_words

    @staticmethod
    def sentence_tokenizer(paragraph):
        return sent_tokenize(paragraph)

    @staticmethod
    def simplify_url(url):
        url = url.lower().strip().replace('https', '').replace('http', '').replace('www', '').replace('://', '')
        url = h.remove_nonalphanumeric(url, '')
        return url

    @staticmethod
    def word_tokenizer(paragraph: str, remove_stopwords: bool = True):
        paragraph = str(paragraph).replace('-', '')
        all_tokens = word_tokenize(paragraph)
        if remove_stopwords:
            no_stopwords = tools.remove_stopwords(all_tokens)
            words = [word.lower() for word in no_stopwords if word.isalnum()]
        else:
            words = [word.lower() for word in all_tokens if word.isalnum()]
        return words


    @staticmethod
    def is_country_in_affiliation(country, full_affiliation):
        c = set(country)
        a = set(full_affiliation)
        return c.issubset(a)

    @staticmethod
    def stem_text(paragraph, apply_stemming=True, remove_stopwords=True):
        words = tools.word_tokenizer(paragraph.lower(), remove_stopwords=remove_stopwords)
        if apply_stemming:
            words = [stemmer.stem(w) for w in words]
        t = ' '.join(words)
        return t


    @staticmethod
    def _gen_fake_google_id():
        return hashlib.md5(str(random.random()).encode('utf-8')).hexdigest()[:16]

    @staticmethod
    def _rename_last_downloaded_file(folder_path, new_filename):
        list_of_files = glob.glob(folder_path + '\\*')  # * means all if need specific format then *.csv
        latest_file = max(list_of_files, key=os.path.getctime)
        shutil.move(os.path.join(folder_path, latest_file), new_filename)

    @staticmethod
    def ignore_exception(IgnoreException=Exception, DefaultVal=0):
        """ Decorator for ignoring exception from a function
        e.g.   @ignore_exception(DivideByZero)
        e.g.2. ignore_exception(DivideByZero)(Divide)(2/0)
        """

        def dec(function):
            def _dec(*args, **kwargs):
                try:
                    return function(*args, **kwargs)
                except IgnoreException:
                    return DefaultVal

            return _dec

        return dec

    @staticmethod
    def force_timeout(self):
        """Works only on Windows"""
        os.system('taskkill /im firefox.exe /f /t')

    @staticmethod
    def _get_browser_header():
        gid = tools._gen_fake_google_id()
        ua = tools.get_stripped_useragent()
        headers = {
            'Connection': 'close',  # another way to cover tracks
            'User-Agent': ua,
            'Cookie': 'GSP=ID=%s:CF=4' % gid,
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        return headers

    @staticmethod
    def download_page(url, filename=None, search=None, return_string=False, add_headers: bool = True):
        if filename is None:
            filename = tools.html_filename(url)
        final_url = url
        if os.path.isfile(filename) and os.stat(filename).st_size > 0 and search.force_crawl is False:
            h.log_line('File exists:', filename, 'Skipping download of', url)
            s = h.read_file(filename)
        else:
            h.log_line('Downloading', url, 'to', filename)
            if not add_headers:
                r = requests.get(url, allow_redirects=True, timeout=60)
            else:
                r = requests.get(url, allow_redirects=True, timeout=60, headers=tools._get_browser_header())
            final_url = r.url
            # content = html.fromstring(r.content)
            with open(filename, 'wb') as f:
                f.write(r.content)
            s = r.content
        if return_string:
            web_page = s
        else:
            web_page = html.fromstring(s)
        return web_page, final_url

    @staticmethod
    def get_data_from_api(url: str, folder: str, add_headers: bool = True):
        """
        Download the data from an API with the provided URL and save it to the provided folder.
        :param url:
        :param folder:
        :param add_headers:
        :return:
        """
        filename = os.path.join(folder, tools.html_filename(url))
        if os.path.isfile(filename) and os.stat(filename).st_size > 0:
            h.log_line('File exists:', filename, 'Skipping download of', url)
            json_data = h.read_file(filename)
        else:
            h.log_line('Downloading', url, 'to', filename)
            if not add_headers:
                r = requests.get(url, allow_redirects=True, timeout=60)
            else:
                r = requests.get(url, allow_redirects=True, timeout=60, headers=tools._get_browser_header())
            json_data = r.content
            with open(filename, 'wb') as f:
                f.write(json_data)

        try:
            data = json.loads(json_data)
        except Exception as ex:
            h.log_line(ex)
            data = None

        return data

    @staticmethod
    def html_filename(url, folder=None):
        sr = urllib.parse.urlsplit(url)
        filename = sr.path
        if len(sr.query) > 0:
            filename += '_' + sr.query
        filename = slugify(filename) + '.html'
        if folder:
            filename = os.path.join(folder, filename)
        return filename

    @staticmethod
    def json_filename(url, folder=None):
        sr = urllib.parse.urlsplit(url)
        filename = sr.path
        if len(sr.query) > 0:
            filename += '_' + sr.query
        filename = slugify(filename) + '.json'
        if folder:
            filename = os.path.join(folder, filename)
        return filename

    @staticmethod
    def resolve_url(base_url):
        r = requests.get(base_url)
        return r.url

    @staticmethod
    def download_file_wget_external(url, filename=None):
        if filename is None:
            filename = tools.html_filename(url)
        if os.path.isfile(filename) and os.stat(filename).st_size > 0:
            h.log_line('File exists:', filename, 'Skipping download of', url)
        else:
            h.log_line('Downloading', url, 'to', filename)
            # wget -o aal.csv -O aal.csv http://ieeexplore.ieee.org/search/searchExport.jsp?queryText=ambient%20assisted%20living&ranges=2018_2018_Year
            h.safe_exec_bash_cmd(['wget', '-o', filename + '.log', '-O', filename, url])
        return h.read_file(filename)

    @staticmethod
    def download_file_firefox(url, filename=None):
        if filename is None:
            filename = tools.html_filename(url)
        if os.path.isfile(filename) and os.stat(filename).st_size > 0:
            h.log_line('File exists:', filename, 'Skipping download of', url)
        else:
            h.log_line('Downloading', url, 'to', filename)
            tools._download_file_firefox_internal(filename, url)
        return h.read_file(filename)

    @staticmethod
    def _download_file_firefox_internal(filename, url):
        t = Timer(60, tools.force_timeout)
        folder, _ = os.path.split(filename)
        # run force_timeout from new thread after 60 seconds
        t.start()  # start timer
        try:
            fp = webdriver.FirefoxProfile()

            fp.set_preference('browser.download.folderList', 2)
            fp.set_preference('browser.download.manager.showWhenStarting', False)
            fp.set_preference('browser.download.dir', folder)
            fp.set_preference('browser.helperApps.neverAsk.saveToDisk', 'text/csv, text/plain, application/x-bibtex')
            fp.set_preference('browser.download.manager.scanWhenDone', False)
            fp.set_preference('browser.download.manager.showAlertOnComplete', False)
            fp.set_preference('browser.download.manager.useWindow', False)
            fp.set_preference('browser.helperApps.alwaysAsk.force', False)
            # Start the WebDriver and load the page
            binary = FirefoxBinary()
            wd = webdriver.Firefox(firefox_binary=binary, firefox_profile=fp)
            wd.implicitly_wait(2)  # wait for scripts to bind dynamic data
            wd.get(url)
            t.cancel()  # cancel timer
            wd.close()
        except Exception as ex:
            h.log_line(ex)
            pass
        finally:
            t.cancel()  # cancel timer

        tools._rename_last_downloaded_file(folder, filename)

    @staticmethod
    def download_file_wget(url, filename=None):
        if filename is None:
            filename = tools.html_filename(url)
        h.log_line('Downloading', url, 'to', filename)
        if os.path.isfile(filename) and os.stat(filename).st_size > 0:
            h.log_line('File exists:', filename, 'Skipping download of', url)
        else:
            wget.download(url, filename)
        return h.read_file(filename)

    @staticmethod
    def download_file_simple(url, filename=None):
        if filename is None:
            filename = tools.html_filename(url)
        h.log_line('Downloading', url, 'to', filename)
        if os.path.isfile(filename) and os.stat(filename).st_size > 0:
            h.log_line('File exists:', filename, 'Skipping download of', url)
        else:
            r = requests.get(url, allow_redirects=True, stream=True, timeout=60, headers=tools._get_browser_header())
            with open(filename, 'wb') as f:
                # f.write(r.content)
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        return h.read_file(filename)

    @staticmethod
    def download_file_simple2(url, filename=None):
        if filename is None:
            filename = tools.html_filename(url)
        h.log_line('Downloading', url, 'to', filename)
        if os.path.isfile(filename) and os.stat(filename).st_size > 0:
            h.log_line('File exists:', filename, 'Skipping download of', url)
        else:
            urlretrieve(url, filename)
        return h.read_file(filename)

    @staticmethod
    def clean_string(s):
        if s is None:
            s = ''
        try:
            s = h.list_to_str(s, ' ').replace('\\xa0', '')
            s = h.remove_tabs(s)
        except Exception as e:
            s = ''
        if h.is_empty(s):
            s = ''
        return s

    @staticmethod
    def clean_and_strip_string(s):

        return tools.clean_string(s).strip()

    @staticmethod
    def text_to_tuple(abstract):
        words = word_tokenize(abstract)
        country_words = tuple(words)
        return country_words

    @staticmethod
    def text_to_tuple_permutations(phrase, apply_permutations=True):
        stemmed_synonym_tuple = tools.text_to_tuple(phrase)
        if apply_permutations:
            stemmed_synonym_np = np.array(stemmed_synonym_tuple)
            perm_list = [list(p) for p in permutations(range(len(stemmed_synonym_tuple)))]
            phrase_tuples = [tuple(stemmed_synonym_np[p]) for p in perm_list]
        else:
            phrase_tuples = [stemmed_synonym_tuple]
        return phrase_tuples

    @staticmethod
    def df_as_str(df):
        df = df.astype(str)
        df.replace(to_replace=[r"\\t|\\n|\\r", "\t|\n|\r"], value=["", ""], regex=True, inplace=True)
#
# n = 0
# for x in Countries.country_map:
#     for y in Countries.country_map:
#         if x != y and tools.is_subsequence(x, y):
#             n += 1
#             print(n, x, y)
# print(max([len(x) for x in Countries.country_map]))
# print(Countries.process_affiliations(
#     """Faculty of Computer Science and Engineering, Saints Cyril and Methodius University, Skopje, Macedonia; Faculty of Computer Science and Engineering, Saints Cyril and Methodius University, Skopje, Macedonia; Faculty of Computer Science and Engineering, Saints Cyril and Methodius University, Skopje, Macedonia; Faculty of Computer Science and Engineering, Saints Cyril and Methodius University, Skopje, Macedonia; Faculty of Computer Science and Engineering, Saints Cyril and Methodius University, Skopje, Macedonia; Faculty of Telecommunications, Technical University of Sofia, Sofia, Bulgaria; Department of Informatics, Instituto de Telecomunicações and ALLab Assisted Living Computing and Telecommunications Laboratory, Universidade da Beira Interior, Covilhã, Portugal; Department of Informatics, Instituto de Telecomunicações and ALLab Assisted Living Computing and Telecommunications Laboratory, Universidade da Beira Interior, Covilhã, Portugal""")[-2])
#
# print(Countries.process_affiliations("""a Rehabilitation Science & Technology , University of Pittsburgh , Pittsburgh , PA , USA.;a Rehabilitation Science & Technology , University of Pittsburgh , Pittsburgh , PA , USA.;a Rehabilitation Science & Technology , University of Pittsburgh , Pittsburgh , PA , USA.;a Rehabilitation Science & Technology , University of Pittsburgh , Pittsburgh , PA , USA.;a Rehabilitation Science & Technology , University of Pittsburgh , Pittsburgh , PA , USA.;a Rehabilitation Science & Technology , University of Pittsburgh , Pittsburgh , PA , USA.;b Management Sciences for Health , Arlington , VA , USA.;c The Institute for Performance Improvement , Downers Grove , IL , USA.""")[-2])

# print(Countries.process_affiliations(
#     """Centers for Disease Control and Prevention, Atlanta, Georgia;tlh9@cdc.gov.;Minnesota Department of Health, St Paul, Minnesota;;Department of Population Medicine, Harvard Medical School and Harvard Pilgrim Healthcare Institute, Boston, Massachusetts;;Public Health Division, Oregon Health Authority Portland, Oregon;;Colorado Department of Public Health and Environment, Denver, Colorado;;Connecticut Department of Public Health, Hartford, Connecticut;;New Mexico Department of Health, Santa Fe, New Mexico;and.;New York State Department of Health, Albany, New York.;Centers for Disease Control and Prevention, Atlanta, Georgia;;Centers for Disease Control and Prevention, Atlanta, Georgia;""")[
#           -2])
# print(Countries.process_affiliations("""""")[-2])

# print(Countries.process_affiliations("""Centers for Disease Control and Prevention, Atlanta, Georgia;tlh9@cdc.gov.;Minnesota Department of Health, St Paul, Minnesota;;Department of Population Medicine, Harvard Medical School and Harvard Pilgrim Healthcare Institute, Boston, Massachusetts;;Public Health Division, Oregon Health Authority Portland, Oregon;;Colorado Department of Public Health and Environment, Denver, Colorado;;Connecticut Department of Public Health, Hartford, Connecticut;;New Mexico Department of Health, Santa Fe, New Mexico;and.;New York State Department of Health, Albany, New York.;Centers for Disease Control and Prevention, Atlanta, Georgia;;Centers for Disease Control and Prevention, Atlanta, Georgia;""")[-2])
# print(tools.is_subsequence((1,2,3),(1,2,3,4,5,6)))
# print(tools.is_subsequence((1,2,3),(2,2,3,4,5,6)))
# print(tools.is_subsequence((1,2,3,4,5,6),(1,2,3)))
# print(tools.is_subsequence((1,2,3),(1,2,3)))
