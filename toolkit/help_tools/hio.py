import csv
import glob
import io
import os
import shutil
import time
from pathlib import Path
from typing import Union, Dict

import chardet
import pandas as pd

from help_tools import helpers as h


def archive_old_results(folder_results: str):
    archive = os.path.join(folder_results, 'archive')
    h.create_folder(archive)
    patterns = ['aggr*pdf', 'aggr*png', '*prisma*', 'aggr*csv', 'aggr*xlsx', '*bib', '*txt', '*json', '*pickle',
                'plot*', '*searched*', 'filtered_articles.xlsx', 'filtered_property_groups.xlsx',
                'filtered_graph*spring*', 'filtered_graph_data.csv', 'filtered_articles_graphs/']
    files = set()
    for p in patterns:
        pfiles = glob.glob(os.path.join(folder_results, p))
        files.update(set(pfiles))
    for f in files:
        fn = h.get_filename(f)
        if fn == 'log.txt':  # skip the log.txt file because it is still open and we log information there
            continue
        f_new = os.path.join(archive, fn)
        h.log_line(f'Trying to move from {f} to {f_new}')
        h.move_file_or_folder(f, f_new)


def archive_folder(folder_name: str, number_of_archives_to_retain: int = 5):
    """
    Move all files and folders from the
    :param folder_name: Which folder to archive?
    :param number_of_archives_to_retain: How many previous archives to retain? If None, it keeps all of them.
    :return:
    """
    # Create archive folder if it doesn't exist
    archive_folder_path = os.path.join(folder_name, 'archive')
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    archive_folder_timestamp = os.path.join(archive_folder_path, timestamp)
    h.create_folder(archive_folder_timestamp)

    # Move the old results into archive folder
    result_folder_path = Path(folder_name)
    for path in result_folder_path.iterdir():
        if path.is_file():
            fn = h.get_filename(path)
            if fn == 'log.txt':  # skip the log.txt file because it is still open and we log information there
                continue
            shutil.move(str(path), archive_folder_timestamp)  # Moving the file
        elif path.is_dir() and str(path) != archive_folder_path:
            shutil.move(str(path), archive_folder_timestamp)  # Moving the directory that is not archive

    # Keep only the last 5 archived results
    if number_of_archives_to_retain > 0:
        archive_folder_path = Path(archive_folder_path)
        old_timestamp_directories = list()
        for path in archive_folder_path.iterdir():
            if path.is_dir():  # Collecting previous archived directories
                try:
                    timestamp_directory = os.path.basename(os.path.normpath(str(path)))
                    time.strptime(timestamp_directory, "%Y%m%d-%H%M%S")
                    old_timestamp_directories.append(path)
                except ValueError:
                    pass  # The directory does not fit the filename pattern
        old_timestamp_directories.sort(reverse=True)
        for old_timestamp_directory in old_timestamp_directories[number_of_archives_to_retain:]:
            shutil.rmtree(old_timestamp_directory)


def detect_encoding(filename, n_lines=20, default_encoding='windows-1251'):
    """Predict a file's encoding using chardet"""
    if not os.path.exists(filename):
        with open(filename, 'wb') as f:
            pass  # Create an empty file
    # Open the file as binary data
    with open(filename, 'rb') as f:
        # Join binary lines for specified number of lines
        rawdata = b''.join([f.readline() for _ in range(n_lines)])

    encoding = chardet.detect(rawdata)['encoding']
    h.log_line('Detected encoding:', encoding, 'in', filename)
    valid = False
    for ok_encoding in ('utf-8', 'windows-1251', 'utf-16'):
        if ok_encoding in encoding.lower() or encoding.lower() in ok_encoding:
            valid = True
            break
    encoding2 = encoding if valid else default_encoding
    h.log_line('Detected encoding:', encoding, '. Using encoding:', encoding2, 'in', filename)
    return encoding2


def get_extension(filename):
    fn, extensn = os.path.splitext(filename)
    return extensn.lstrip('.')


def pd_read_csv_or_string_stream(filename: Union[str, io.StringIO], sep='\t', encoding: str = None,
                                 dtypes: Dict = None, quoting=csv.QUOTE_MINIMAL, usecols=None,
                                 escapechar: str = None, quotechar: str = '"') -> pd.DataFrame:
    if quotechar is None:
        quoting = csv.QUOTE_NONE

    if isinstance(filename, str):
        if encoding is None:
            encoding = detect_encoding(filename)
        df = pd.read_csv(filename, header=0, encoding=encoding, sep=sep, dtype=dtypes, quoting=quoting,
                         usecols=usecols, escapechar=escapechar, quotechar=quotechar, on_bad_lines='warn')
    else:
        df = pd.read_csv(filename, header=0, encoding=encoding, sep=sep, dtype=dtypes, quoting=quoting, usecols=usecols,
                         escapechar=escapechar, quotechar=quotechar, on_bad_lines='warn')

    return df


def pd_read_csv_or_excel(filename: str, sep='\t', encoding: str = None, dtypes: Dict = None, quoting=csv.QUOTE_MINIMAL,
                         usecols=None, escapechar: str = None, quotechar: str = '"') -> pd.DataFrame:
    """
    Read csv or excel file into pandas dataframe

    :param filename: The location of the file
    :type filename: str
    :param sep: Delimiter to use for csv file
    :type sep: str
    :param encoding: Encoding to use for csv file
    :type encoding: str
    :param dtypes: Data type for the columns
    :type dtypes: Dict
    :param quoting: Control field controlling the quoting behaviour
    :type quoting: csv.QUOTE
    :param usecols: Subset of the columns
    :type usecols: List[str]
    :param escapechar: One-character string used to escape other characters
    :type escapechar: str
    :param quotechar: The character used to denote the start and end of a quoted item
    :type quotechar: str

    :return: The content of the file
    :rtype: pd.DataFrame
    """

    file_extension = get_extension(filename).lower()
    if file_extension in ('xlsx', 'xls'):
        df = pd.read_excel(filename, header=0, usecols=usecols, dtype=dtypes, na_filter=False)
    elif file_extension in ('csv', 'txt'):
        if quotechar is None:
            quoting = csv.QUOTE_NONE
        if encoding is None:
            encoding = detect_encoding(filename)
        df = pd.read_csv(filename, header=0, encoding=encoding, sep=sep, dtype=dtypes, quoting=quoting,
                         usecols=usecols, escapechar=escapechar, quotechar=quotechar, on_bad_lines='warn',
                         na_filter=False)
    else:
        raise Exception("Unsupported file format for file: ", filename)

    return df


def df_to_csv(df, csvFilePath, sep="\t", mode='w', write_to_excel_too=False, index=False):
    import os
    if mode == 'w':
        df.to_csv(csvFilePath, index=False, sep=sep)
    elif not os.path.isfile(csvFilePath):
        df.to_csv(csvFilePath, mode='a', index=False, sep=sep)
    elif len(df.columns) != len(pd.read_csv(csvFilePath, nrows=1, sep=sep).columns):
        raise Exception(
            "Columns do not match!! Dataframe has " + str(len(df.columns)) + " columns. CSV file has " + str(
                len(pd.read_csv(csvFilePath, nrows=1, sep=sep).columns)) + " columns.")
    elif not (df.columns == pd.read_csv(csvFilePath, nrows=1, sep=sep).columns).all():
        raise Exception("Columns and column order of dataframe and csv file do not match!!")
    else:
        df.to_csv(csvFilePath, mode='a', index=False, sep=sep, header=False)
    if write_to_excel_too:
        h.csv_to_excel(csvFilePath, sep)
