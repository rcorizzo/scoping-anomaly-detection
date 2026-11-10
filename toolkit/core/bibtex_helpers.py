from help_tools import helpers as h
from core.search_config import SearchConfig
from help_tools.tools import tools
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
import pandas as pd


def create_bibtex_entries(search: SearchConfig, df: pd.DataFrame = None):
    """
    Tokenizing articles to create bibtex entries
    :param search:
    :param df:
    :return:
    """
    h.log_line('Generating bibtex...')
    search.set_status('Create bibtex entries', 'Starting')
    if df is None:
        df = pd.read_csv(search.file_articles_all, sep='\t')
    bibtex_db = BibDatabase()
    bibtex_writer = BibTexWriter()

    bibtex_doi_ids = {}
    bibtex_id_counter = 0
    bibtex_ids_list = []
    bibtex_ids_dict = {}
    valid_rows = []
    for i, row in df.iterrows():
        bibtex_id = ""
        cbibtex_content = ""
        try:
            authors_tokens = tools.word_tokenizer(row.authors)
            authors_key = ''
            for auth in authors_tokens:
                authors_key += auth
                if len(authors_key) > 5:
                    break
            # Generate google scholar-like keys: lawrence1999digital
            title_token = tools.word_tokenizer(row.title)
            if len(title_token) == 0:
                title_token = ['']
            bibtex_id_base = str(authors_key) + str(row.year) + str(title_token[0])
            bibtex_id = h.remove_nonalpha(bibtex_id_base, '').replace(' ', '')
            while bibtex_id in bibtex_ids_dict:
                bibtex_id_counter += 1
                bibtex_id = bibtex_id_base + str(bibtex_id_counter)

            bibtex_db.entries = [
                dict(title=str(row.title), author=str(row.authors), year=str(row.year), ID=bibtex_id,
                     publisher=row.source.replace(' Xplore', '').replace('NCBI:', ''),
                     journal=str(row.publication_title).replace('nan', ''),
                     doi=str(row.doi), url=str(row.link), ENTRYTYPE='article')]
            cbibtex_content = bibtex_writer.write(bibtex_db)
            bibtex_ids_dict[bibtex_id] = cbibtex_content
            bibtex_doi_ids[row.doi] = bibtex_id
            bibtex_ids_list.append(bibtex_id)
            valid_rows.append(i)
        except Exception as e:
            h.log_line('Invalid row', i, len(row), row, e)
            bibtex_ids_dict[bibtex_id] = cbibtex_content
            bibtex_doi_ids[row.doi] = bibtex_id
            bibtex_ids_list.append(bibtex_id)
    df['bibtex_id'] = bibtex_ids_list

    h.to_pickle((bibtex_ids_dict, bibtex_doi_ids), search.filename_bibtex_temp)
    search.to_pickle()
    search.set_status('Create bibtex entries')
    h.log_line('Create bibtex entries:')
    return bibtex_ids_dict, bibtex_doi_ids


def generate_bibtex_file(search: SearchConfig, bibtex_ids, bibtex_doi_ids, retained_dois):
    search.set_status('Generate bibtex', 'Starting')
    with open(search.file_articles_bib, 'w', encoding='utf8') as bibfile:
        for i, doi in enumerate(retained_dois):
            try:
                bib_entry = bibtex_ids[bibtex_doi_ids[doi]]
                bibfile.write(bib_entry)
            except Exception as e:
                h.log_line('Invalid entry:', i, type(doi), doi, 'Exception:', e)
    search.set_status('Generate bibtex')
