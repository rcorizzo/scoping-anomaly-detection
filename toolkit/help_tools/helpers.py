# -*- coding: utf-8 -*-
# !/usr/bin/python
# import number_padding
import ast
import csv
import datetime
import hashlib
import json
import logging
import logging.config
import math
import operator
import os.path
import pickle
import pprint
import re
import shutil
import threading
import time
from os import listdir
from os.path import isfile, join

import bibtexparser
import jsonpickle
import numpy as np
import pandas as pd
import pytz
from pytz import timezone

# regex_emails = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
regex_emails = re.compile(r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|(\\[\t -~]))+\")@([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\[[\t -Z^-~]*])")


def xml2dict(xml_file, xml_attribs=True):
    import xmltodict
    with open(xml_file, "rb") as f:  # notice the "rb" mode
        d = xmltodict.parse(f, xml_attribs=xml_attribs)
        return d


re_non_alpha_numeric = re.compile(r'[^0-9a-zA-Z]+', re.MULTILINE | re.IGNORECASE)
re_non_alpha = re.compile(r'[^a-zA-Z]+', re.MULTILINE | re.IGNORECASE)
re_num = re.compile(r"[^0-9]")
re_white = re.compile(r"\s+", re.MULTILINE)
re_tabs = re.compile(r"[\t\n\v\r]+", re.MULTILINE)


def remove_tabs(s):
    s = str(s)
    try:
        s1 = re_tabs.sub(' ', s)
        s2 = re_white.sub(' ', s1)
        return s2
    except Exception as e:
        log_line('Error with string:', s, e)
        return ''


def is_email_valid(email):
    try:
        if re.fullmatch(regex_emails, email):
            return True
        else:
            return False
    except:
        return False


def remove_nonalpha(s, sub='', lower=True):
    if s is None:
        return ''
    if lower:
        s = s.lower()
    s1 = re_non_alpha.sub(sub, s)
    return s1


def remove_nonalphanumeric(s, sub=' '):
    if s is None:
        return ''
    s1 = re_non_alpha_numeric.sub(sub, s)
    s2 = re_white.sub(sub, s1)
    return s2


def remove_non_numeric(s, sub=''):
    if s is None:
        return ''
    s1 = re_num.sub(sub, s)
    return s1


def fstr(f, digits=7):
    """Float to string"""
    # if 'tuple' in str(type(f)) or 'str' in str(type(f)):
    #     frs = str(f)
    # if 'float' in str(type(f)):
    if is_empty(f):
        return ''
    if is_float(f):
        if digits is None:
            digits = 7
        format = '%.' + str(digits) + 'f'
        frs = format % float(f)
        frs = frs.rstrip('0').rstrip('.')
    else:
        frs = str(f)
    return frs


def sencode(x):
    try:
        res = x.encode('utf-8')
        # res = unicode(x, 'utf8', errors='ignore')
    except:
        # res = unicode(x)
        # res = res.encode('utf-8')
        # log_line('GRESKA', x)
        res = x

    return res


def is_zero(f, digits=10):
    return abs(float(f)) < pow(10, -digits)


def equal_float(f, x, digits=10):
    return abs(float(f) - float(x)) < pow(10, -digits)


def move(src, dest):
    try:
        log_line('Moving', src, 'to', dest)
        from shutil import move
        move(src, dest)
    except Exception as e:
        log_line('Moving failed because:', e)


def md5hash(s, to_int=False):
    """
    Calculates the md5 hash of s and returns a long int
    :rtype : object
    :param s:
    :param to_int: if true it returns the integer representation of the hash
    :return:
    """
    md5 = hashlib.md5()
    md5.update(sencode(fstr(s)))
    digest = md5.hexdigest()
    if to_int:
        number = int(digest, 16)
        return number
    else:
        return fstr(digest)


# key=''
# print(h.md5hash('Canada'+key))
# print(h.md5hash('Canada'+key, True))
# print(h.md5hash('Canada'+key, True) % 1000)
#
# key='Rachel McAdams plays in True Detective along with Colin Farrell'
# print(h.md5hash('Canada'+key))
# print(h.md5hash('Canada'+key, True))
# print(h.md5hash('Canada'+key, True) % 1000)
#
# key='Rachel McAdams plays in True Detective along with Colin Farrell'
# print(h.md5hash('99.95'+key))
# print(h.md5hash('99.95'+key, True))
# print(h.md5hash('99.95'+key, True) % 1000)

def is_file(filename):
    try:
        return filename is not None and os.path.isfile(filename) and os.stat(filename).st_size > 0
    except:
        print(filename)
        exit(1)


def remove_extension(filename):
    fn, _ = os.path.splitext(filename)
    return fn


def to_pickle(instance, filename):
    with open(filename, 'wb') as f:
        pickle.dump(instance, f)


def from_pickle(filename):
    with open(filename, 'rb') as f:
        instance = pickle.load(f)
    return instance


def to_json(instance, json_file=None, pretty_print=False):
    json_string = jsonpickle.encode(instance)
    if pretty_print:
        json_string = json.dumps(json.loads(json_string), indent=4)
    if json_file is not None:
        with open(json_file, mode='w', encoding='utf8') as f:
            f.write(json_string)
    return json_string


def pretty_print(instance):
    desired_quote = '"'
    replaced_qoute = "'"
    s = json.dumps(instance)
    s1 = s.replace(replaced_qoute, "EFTIM_TMP_QOUTE")
    d = ast.literal_eval(s1)
    pp = pprint.PrettyPrinter(width=160)
    json_string = pp.pformat(d)
    final_string = json_string.replace(replaced_qoute, desired_quote).replace("EFTIM_TMP_QOUTE", replaced_qoute)
    return final_string


def to_json_simple(instance, json_file=None):
    if isinstance(instance, dict):
        json_string = pretty_print(instance)
    else:
        json_string = json.dumps(instance, sort_keys=True, indent=4)
    if json_file is not None:
        with open(json_file, mode='w', encoding='utf8') as f:
            f.write(json_string)
    return json_string


def from_json(json_string=None, json_file=None):
    if json_file is None and json_string is None:
        log_line('Both json_file and json_string are None')
        return None
    if json_string is None:
        with open(json_file) as f:
            json_string = f.read()
    decoded_object = jsonpickle.decode(json_string)
    return decoded_object


def from_json_simple(json_string=None, json_file=None):
    if json_file is None and json_string is None:
        log_line('Both json_file and json_string are None')
        return None
    if json_string is None:
        with open(json_file, encoding='utf8') as f:
            # decoded_object = json.load(f)
            json_string = f.read()
    # decoded_object = json.loads(json_string, encoding='utf8')
    decoded_object = ast.literal_eval(json_string)
    return decoded_object


# j=from_json_simple(json_file='/Users/eftim/Repositories/survey-results/results/results_AAL_20180930_AAPELE/keywords_searched.txt')
# to_json_simple(j,json_file='/Users/eftim/Repositories/survey-results/results/results_AAL_20180930_AAPELE/keywords_searched.txt')
def open_file_externally(filepath):
    try:
        import subprocess, os, sys
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', filepath))
        elif os.name == 'nt':
            # windows
            os.startfile(filepath)
            # os.system("start " + filepath)
        elif os.name == 'posix':
            # Linux
            subprocess.call(('xdg-open', filepath))
    except Exception as e:
        log_line('Unable to open external file:', filepath, e)


def to_pickle(instance, pickle_file):
    import pickle
    with open(pickle_file, mode='wb') as f:
        pickle.dump(instance, f)


def from_pickle(pickle_file: str):
    import pickle
    with open(pickle_file, "rb") as f:
        obj = pickle.load(f)
    return obj


def to_json_jw(instance, json_file=None):
    # json_string = jsonpickle.encode(instance)
    from jsonweb import dumper
    json_string = dumper(instance)
    if json_file is not None:
        with open(json_file, mode='w') as f:
            f.write(json_string)
    return json_string


def from_json_jw(json_string=None, json_file=None):
    if json_file is None and json_string is None:
        return None
    if json_string is None:
        with open(json_file) as f:
            json_string = f.readlines()[0]

    # decoded_object = jsonpickle.decode(json_string)
    from jsonweb import loader
    decoded_object = loader(json_string)
    return decoded_object


def parse_date_time(date_time_str):
    # h.log_line('Date:',date_time_str)
    dt_regex1 = re.compile(r'(\d\d)[.|-](\d\d)[.|-](\d\d\d\d) (\d\d):(\d\d)(:\d\d)?')
    dt_regex2 = re.compile(r'(\d\d\d\d)[.|-](\d\d)[.|-](\d\d) (\d\d):(\d\d)(:\d\d)?')
    # h.log_line(date_time_str)
    match1 = dt_regex1.search(date_time_str)
    match2 = dt_regex2.search(date_time_str)
    if match1:
        match = match1
        year = int(match.group(3))
        month = int(match.group(2))
        day = int(match.group(1))
        hour = int(match.group(4))
        minute = int(match.group(5))
        second = int(match.group(6).strip(':')) if match.group(6) else 0
        return datetime.datetime(year, month, day, hour, minute, second)
    elif match2:
        match = match2
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        second = int(match.group(6).strip(':')) if match.group(6) else 0
        return datetime.datetime(year, month, day, hour, minute, second)
    else:
        # log_line('No match:',date_time_str)
        return None


def is_int(s):
    """
    Checks if the argument is an integer
    """
    try:
        int(s)
        return True
    except ValueError:
        return False


def is_float(s):
    """
    Checks if the argument is an float
    """
    try:
        float(s)
        return True
    except:
        return False


def str_to_tup(s):
    s = s.lstrip('(').rstrip(')')
    vals = s.split(',')
    t = []
    for v in vals:
        vs = auto_cast(v.strip())
        if not vs == '':
            t.append(vs)
    return tuple(t)


def auto_cast(s):
    try:
        t = int(s)
        return t
    except ValueError:
        try:
            t = float(s)
            return t
        except ValueError:
            t = str(s)
            return t.strip('"').strip("'")


def is_true(s):
    """
    Checks if the argument is a boolean with True value
    """
    if 'bool' in str(type(s)) and s:
        return True
    elif isinstance(s, str) and s.lower() in {'true', '1'}:
        return True
    else:
        return False


def mean(l):
    if len(l) == 0:
        return 0
    return sum(l) / float(len(l))


def min_max_sum(l):
    n = len(l)
    if n == 0:
        return [0, 0, 0]
    mn = l[0]
    mx = l[0]
    s = l[0]
    for i in range(1, n):
        s += l[i]
        if l[i] < mn:
            mn = l[i]
        if l[i] > mx:
            mx = l[i]

    return [mn, mx, s]


def min_max_sum_fd(l):
    """Computes the min, max, sum, first derivative min, first derivative max, first derivative sum.

    :param l: list of values.
    """

    n = len(l)
    if n == 0:
        return [0, 0, 0, 0, 0, 0]
    value_min = l[0]
    value_max = l[0]
    value_sum = l[0]
    if n == 1:
        return [value_min, value_max, value_sum, 0, 0, 0]
    fd_min = l[1] - l[0]
    fd_max = fd_min
    fd_sum = fd_min
    for i in range(1, n):
        value_sum += l[i]
        if l[i] < value_min:
            value_min = l[i]
        if l[i] > value_max:
            value_max = l[i]
        if i < n - 1:
            fd_curr = l[i + 1] - l[i]
            fd_sum += fd_curr
            if fd_curr < fd_min:
                fd_min = fd_curr
            if fd_curr > fd_max:
                fd_max = fd_curr

    return [value_min, value_max, value_sum, fd_min, fd_max, fd_sum]


def min_max_mean(l):
    n = len(l)
    if n == 0:
        return [0, 0, 0]
    mn = l[0]
    mx = l[0]
    s = l[0]
    for i in range(1, n):
        s += l[i]
        if l[i] < mn:
            mn = l[i]
        if l[i] > mx:
            mx = l[i]

    avg = s / float(n)
    return [mn, mx, avg]


def stdev(l, list_mean=None):
    n = len(l)
    if n == 0:
        return 0
    if list_mean is None:
        list_mean = mean(l)
    sum_sqares = 0
    for x in l:
        sum_sqares += (x - list_mean) ** 2
    std = (sum_sqares / float(n)) ** 0.5
    return std


def parse_labels_line(line):
    labels = line.split(',')
    result = dict()
    result['label1'] = labels[0]
    result['label2'] = labels[1]
    result['labelps'] = result['label1'] + '+' + result['label2']
    return result


#
# def open_csv_file(sql_filename, datatype='float'):
#     """
#     Only for python 2.7
#     :param sql_filename:
#     :param datatype:
#     :return:
#     """
#     ds_orig = file(sql_filename, 'r')
#     r = csv.reader(ds_orig)
#     values_list = []
#     for values_line in r:
#         if datatype == 'float':
#             values_line_f = list(map(float, values_line))
#             values_list.append(values_line_f)
#         else:
#             values_list.append(values_line)
#     return values_list


def num_digits(number):
    """
    Calculates log with base 10 so we can get the number of digits of a number
    """
    digits = 0
    if number > 0:
        digits = int(math.ceil(math.log(number) / math.log(10)))

    return digits


def pad_number(number, pad_digits, prefix=''):
    """
    Pads a number with 0s to the number of desired digits. It also adds a prefix if it's provided.
    """
    f = '%0' + str(int(pad_digits)) + 'd'
    padded_number = prefix + (f % int(number))
    return padded_number


def file_has_header(filename, header):
    if not os.path.isfile(filename):
        return False
    with open(filename, newline='') as f:
        for values_line in f:
            reg = re.compile(r'[^a-z0-9]+', re.IGNORECASE)
            v1 = reg.sub('', values_line)
            v2 = reg.sub('', list_to_str(header))
            if v1 == v2:
                return True
            else:
                return False


def load_labels(labels_filename):
    f = open(labels_filename, newline='')
    r = csv.reader(f)
    y1 = []
    y2 = []
    yps = []
    for values_line in r:
        y1.append(values_line[0])
        y2.append(values_line[1])
        yps.append(values_line[0] + ',' + values_line[1])
    f.close()
    return [y1, y2, yps]


def roundup_line(line, digits):
    values = line.split(',')
    val_round = ''
    n = len(values)
    i = 0
    for v in values:
        if is_float(v):
            val_round += fstr(float(v), digits)
        else:
            val_round += v
        if i < n - 1:
            val_round += ','
        i += 1
    return val_round


def longest_common_substring(s1, s2):
    m = [[0] * (1 + len(s2)) for i in range(1 + len(s1))]
    longest, x_longest = 0, 0
    for x in range(1, 1 + len(s1)):
        for y in range(1, 1 + len(s2)):
            if s1[x - 1] == s2[y - 1]:
                m[x][y] = m[x - 1][y - 1] + 1
                if m[x][y] > longest:
                    longest = m[x][y]
                    x_longest = x
            else:
                m[x][y] = 0
    return s1[x_longest - longest: x_longest]


def csv2arff_merge(data_filename, labels_filename):
    data = open(data_filename)
    labels = open(labels_filename)
    arff_filename = data_filename.rstrip('.csv') + ".arff"
    arff_writer = open(arff_filename, 'w')
    both_files = zip(data, labels)

    (current_label_stats, stats_filename) = label_stats(labels_filename)
    labels_string = ','.join([k for k in current_label_stats.keys()])
    arff_writer.write('@RELATION ' + data_filename + '\n\n\n')

    i = 0
    # Get List of all the unique items from the Input
    for data_line, labels_line in both_files:
        if i == 0:
            values = data_line.split(',')
            n = len(values)
            digits = num_digits(n)
            for j in range(0, n - 1):
                arff_writer.write('@ATTRIBUTE a' + pad_number(j, digits) + ' NUMERIC\n')
            arff_writer.write('@ATTRIBUTE class {' + labels_string + '}\n')
            arff_writer.write('\n@DATA\n\n')

        i += 1

        data_values_round = roundop_line(data_line, 5)
        arff_writer.write(str.rstrip(data_values_round, '\n') + ',' + labels_line)

    arff_writer.close()
    data.close()
    labels.close()


def csv2arff(csv_filename, labels_filename):
    csv_file = open(csv_filename)
    arff_filename = csv_filename.rstrip('.csv') + ".arff"
    arff_writer = open(arff_filename, 'w')

    (current_label_stats, stats_filename) = label_stats(labels_filename)
    labels_string = ','.join([k for k in current_label_stats.keys()])
    arff_writer.write('@RELATION ' + csv_filename + '\n\n\n')

    i = 0
    # Get List of all the unique items from the Input
    for line in csv_file:
        if i == 0:
            values = line.split(',')
            n = len(values)
            digits = num_digits(n)
            for j in range(0, n - 1):
                arff_writer.write('@ATTRIBUTE a' + pad_number(j, digits) + ' NUMERIC\n')
            arff_writer.write('@ATTRIBUTE class {' + labels_string + '}\n')
            arff_writer.write('\n@DATA\n\n')

        i += 1
        arff_writer.write(line + '\n')

    arff_writer.close()
    csv_file.close()


def csv2arff_multi_label(csv_filename, labels_filename, label_index):
    csv_file = open(csv_filename)
    arff_filename = csv_filename.rstrip('.csv') + ".arff"
    arff_writer = open(arff_filename, 'w')

    all_stats = labels_stats(labels_filename)
    current_label_stats = all_stats[label_index]
    labels_string = ','.join([k for k in current_label_stats.keys()])
    arff_writer.write('@RELATION ' + csv_filename + '\n\n\n')

    i = 0
    # Get List of all the unique items from the Input
    for line in csv_file:
        if i == 0:
            values = line.split(',')
            n = len(values)
            digits = num_digits(n)
            for j in range(0, n - 1):
                arff_writer.write('@ATTRIBUTE a' + pad_number(j, digits) + ' NUMERIC\n')
            arff_writer.write('@ATTRIBUTE class {' + labels_string + '}\n')
            arff_writer.write('\n@DATA\n\n')

        i += 1
        arff_writer.write(line + '\n')

    arff_writer.close()
    csv_file.close()


def verify_filename(full_filename, ext='.csv'):
    dirname, filename = os.path.split(full_filename)
    if os.path.exists(dirname):
        counter = 1
        full_filename_clean = full_filename
        while os.path.exists(full_filename_clean):
            full_filename_clean = full_filename.replace(ext, '') + '_' + str(counter) + ext
        return full_filename_clean
    return None


write_csv_thread_lock = threading.Lock()


def csv_to_excel(filename, sep='\t'):
    df = pd.read_csv(filename, index_col=None, encoding='utf8', header=0, sep=sep)
    dest_file = remove_extension(filename) + '.xlsx'

    writer = pd.ExcelWriter(dest_file, engine='xlsxwriter')

    # Convert the dataframe to an XlsxWriter Excel object.
    df.to_excel(writer, sheet_name='data', index=False)

    # Get the xlsxwriter objects from the dataframe writer object.
    workbook = writer.book
    worksheet = writer.sheets['data']
    # Add a table to the worksheet.
    # worksheet.add_table('B3:F7', {'data': data})
    # extra_options = {'style': 'Table Style Light 11'}

    columns = [{'header': str(c)} for c in df.columns]
    extra_options = {'name': 'relevant_articles', 'columns': columns}

    # format2 = workbook.add_format({'num_format': '0%'})
    # # Set the format but not the column width.
    # worksheet.set_column('A:A', None, format2)

    worksheet.add_table(0, 0, len(df.index), len(df.columns) - 1, extra_options)
    # Add a bold format to use to highlight cells.
    # bold = workbook.add_format({'bold': 1})
    # worksheet.set_row(0, len(df1.columns)-columns1, bold)
    # worksheet.autofilter(0, 0, len(df1.index)-1, len(df1.columns)-1)
    workbook.close()


def write_csv_file(data, filename, separator=',', mode='w', verbose=1, rounding_decimals=None):
    """
    Compatible with python 2/3
    :param data:
    :param filename:
    :return:
    """
    if data is None:
        data = []
    if 'numpy' in str(type(data)):
        data = data.tolist()
    if verbose > 0:
        log_line('Writing to:', filename, 'Expected lines:', len(data))

    with write_csv_thread_lock:
        with open(filename, mode, encoding='utf8', newline='') as f:
            writer = csv.writer(f, delimiter=separator, quoting=csv.QUOTE_MINIMAL)

            for row in data:
                if rounding_decimals is not None:
                    row = [
                        round(x, rounding_decimals) if isinstance(x, float) else x
                        for x in row
                    ]
                writer.writerow(row)


def write_csv_and_excel_file(data, filename, separator=',', mode='w', verbose=1, rounding_decimals=None):
    write_csv_file(data, filename, separator, mode, verbose, rounding_decimals)
    csv_to_excel(filename, separator)


def create_folder(folder):
    try:
        if not os.path.exists(folder):
            log_line(f"creating folder:{folder}")
            os.makedirs(folder, exist_ok=True)
    except Exception as e:
        log_line("Skipping failed folder creation.", folder, e)


def discretize(min_val, max_val, buckets, value):
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val

    bucket_size = float(max_val - min_val) / float(buckets)
    # decimals = math.log10(bucket_size)
    discrete_val = -abs(min_val) + round((abs(min_val) + value) / bucket_size) * bucket_size

    return discrete_val


def discretize_array(min_val, max_val, buckets, values):
    values[values < min_val] = min_val
    values[values > max_val] = max_val

    bucket_size = float(max_val - min_val) / float(buckets)

    discrete_val = -abs(min_val) + np.around((abs(min_val) + values) / bucket_size, 0) * bucket_size
    discrete_val_round = roundup_array(discrete_val, bucket_size)
    return discrete_val_round


def roundup_array(a, bucket_size):
    digits = int(math.log10(bucket_size))
    if digits > 0:
        decimals = 2
    else:
        decimals = max(2, -digits)
    r = np.around(a, decimals)
    return r


def timestamp():
    start = time.time()
    value = datetime.datetime.fromtimestamp(start)
    starts = (value.strftime('%Y-%m-%d %H:%M:%S'))
    return starts


def timestamp_short():
    start = time.time()
    value = datetime.datetime.fromtimestamp(start)
    starts = (value.strftime('%Y%m%d_%H%M%S'))
    return starts


def exec_bash_cmd(cmd):
    """
    cmd is a string with the full command or a list of main_arguments.
    :param cmd:
    :return:
    """
    from subprocess import check_output, CalledProcessError
    import shlex
    if is_str(cmd):
        args = shlex.split(cmd)
    else:
        args = cmd
        cmd = ' '.join(args)
    try:
        log_line('CMD executing:', cmd)
        # result = check_output(args, shell=True)
        # Not using args because when there are pipes and output redirection it fails
        result = check_output(cmd, shell=True)
        if isinstance(result, bytes):
            result = result.decode('utf8')
        log_line('CMD executed:', cmd, 'RESULT:\n', result)  # , 'CMD args', args)
        return_code = 0
    except CalledProcessError as e:
        log_line('CMD executed:', cmd, 'RESULT:', 'Exception:', str(e))
        return_code = e.returncode
        raise e
    return return_code


def fmt_number(n):
    try:
        n = float(n)
        if n >= 10000:
            return format(int(n), ',d')
        else:
            return ('%f' % n).rstrip('0').rstrip('.')
    except:
        return n


def get_parent_folder(cur_path: str):
    return os.path.dirname(os.path.realpath(cur_path))


def safe_exec_bash_cmd(cmd):
    try:
        r = exec_bash_cmd(cmd)
    except Exception as e:
        log_line('Ignoring the Exception:', e)
        r = -1
    return r


def to_dt_tz_aware(dt):
    if dt.tzinfo is None:
        dta = pytz.utc.localize(dt)
    else:
        dta = dt
    return dta


def dt_tz(my_timezone='utc', dt=None):
    # unaware = datetime.datetime(2011, 8, 15, 8, 15, 12, 0)
    # aware = datetime.datetime(2011, 8, 15, 8, 15, 12, 0, pytz.UTC)
    if dt is None:
        dt = datetime.datetime.now(timezone('UTC'))
    dta = to_dt_tz_aware(dt)
    if my_timezone.lower() in {'toronto', 'ny', 'new york'}:
        tz = timezone('America/Toronto')
    elif my_timezone in pytz.all_timezones_set:
        tz = timezone(my_timezone)
    else:
        tz = timezone('UTC')
    dtl = dta.astimezone(tz)
    return dtl


class RegexHolders(object):
    dt1970ua = datetime.datetime(1970, 1, 1, 0, 0, 0)
    dt1970 = dt_tz('utc', dt1970ua)
    dt_regex_basic = r'\d{4}[-/]\d{2}[-/]\d{2}( |T)\d{2}:\d{2}:\d{2}'
    d_regex_basic = r'\d{4}[-/]\d{2}[-/]\d{2}'
    dt_regex_pattern = dt_regex_basic
    d_regex_pattern = d_regex_basic
    ms_decimals_final = 0
    dt_regex = re.compile(dt_regex_pattern)
    d_regex = re.compile(d_regex_pattern)
    dt_regex_group = re.compile(r'(\d{4})[-/](\d{2})[-/](\d{2})([ T])(\d{2}):(\d{2}):(\d{2})')
    d_regex_group = re.compile(r'(\d{4})[-/](\d{2})[-/](\d{2})')

    @staticmethod
    def get_dt_regex(ms_decimals=0):
        if ms_decimals != RegexHolders.ms_decimals_final:
            ms_decimals = min(ms_decimals, 3)
            RegexHolders.ms_decimals_final = ms_decimals
            RegexHolders.dt_regex_pattern = RegexHolders.dt_regex_basic
            if ms_decimals > 0:
                RegexHolders.dt_regex_pattern += r'\.\d{' + str(ms_decimals) + '}'
            RegexHolders.dt_regex = re.compile(RegexHolders.dt_regex_pattern)
        # log_line(RegexHolders.dt_regex_pattern)
        return RegexHolders.dt_regex

    @staticmethod
    def get_d_regex():
        return RegexHolders.d_regex


def dt_to_str(dt, miliseconds=False):
    # return datetime.datetime.strftime(dt, '%Y-%m-%d %H:%M:%S %Z%z').strip()
    fmt = '%Y-%m-%d %H:%M:%S'
    if miliseconds:
        fmt += '.%f'
    return datetime.datetime.strftime(dt, fmt)


def dt_now():
    dt = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
    return dt


def dt_utc_now():
    dt = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%d %H:%M:%S')
    return dt


def d_now():
    dt = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
    return dt


def dtstr(dt, ms_decimals=0):
    """
    date and time to string
    :param dt:
    :param ms_decimals:
    :return:
    """
    if dt is None:
        return ''
    if not is_str(dt):
        dt = dt_to_str(dt)

    if '0001-01-01' in dt:
        return ''

    regex = RegexHolders.get_dt_regex(ms_decimals)
    match = regex.match(dt)
    if match:
        return match.group().replace('/', '-')
    else:
        return ''


def datediff_seconds(dt1, dt2):
    if dt1 >= dt2:
        return (dt1 - dt2).seconds
    else:
        return (dt2 - dt1).seconds


def is_str(s):
    stype = str(type(s))
    return 'str' in stype or 'unicode' in stype


def dstr(d):
    """date to string"""
    if d is None:
        return ''
    if not is_str(d):
        d = dt_to_str(d)

    if '0001-01-01' in d:
        return ''

    regex = RegexHolders.get_d_regex()
    match = regex.match(d)
    if match:
        # log_line(match)
        return match.group()
    else:
        # SHOMI-41
        # return dt_now()
        return ''


def str_to_dt(dtstr):
    match = RegexHolders.dt_regex_group.search(dtstr)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(5))
        minute = int(match.group(6))
        second = int(match.group(7))
        dt_obj = datetime.datetime(year, month, day, hour, minute, second)
        return dt_obj

    match = RegexHolders.d_regex_group.search(dtstr)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hour = 0
        minute = 0
        second = 0
        dt_obj = datetime.datetime(year, month, day, hour, minute, second)
        return dt_obj
    return None


def setup_logging(
        default_path='help_tools/logging.json',
        default_level=logging.INFO,
        env_key='LOG_CFG',
        output_filename=None
):
    """Setup logging configuration

    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
            if output_filename is not None:
                c = _logger_reset_file(config, output_filename)
                if c is not None:
                    config = c
            logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


setup_logging()
logger = logging.getLogger(__name__)


def path_leaf(path):
    import ntpath
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def _logger_reset_file(config, new_filename):
    try:
        log_line('Reseting log file to:', new_filename)
        config['handlers']['info_file_handler']['filename'] = new_filename
        return config
    except:
        return None


# def get_filename(full_path):
#     try:
#         if full_path is None or '/' not in full_path:  # or not is_str(full_path):
#             full_path = ''
#         p = full_path.rindex('/')
#         if p > 0:
#             return full_path[p + 1:]
#         else:
#             return ''
#     except:
#         return ''

def get_filename(path):
    import ntpath
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


log_thread_lock = threading.Lock()


def log_line(*message):
    m = [fstr(v) for v in message]
    final_message = ' '.join(m)
    "Automatically log the current function details."
    import inspect, logging
    try:
        prev_func = inspect.currentframe().f_back.f_back.f_code
        prev_func_name = prev_func.co_name
        # prev_filename = get_filename(prev_func.co_filename)
    except:
        prev_func_name = ''
    # Get the previous frame in the stack, otherwise it would
    # be this function!!!
    func = inspect.currentframe().f_back.f_code
    # Dump the message + the name of this function to the log.
    filename = path_leaf(func.co_filename)
    with log_thread_lock:
        # logging.info("%s[%s:%i] - %s" % (
        #     func.co_name,
        #     sql_filename,
        #     func.co_firstlineno,
        #     final_message
        # ))
        logging.info("%s[%s:%i]/%s - %s" % (func.co_name,
                                            filename,
                                            func.co_firstlineno,
                                            prev_func_name,
                                            final_message
                                            ))


def log_line_my(*message):
    starts = timestamp()
    m = [str(v) for v in message]
    final_message = starts + ' ' + ' '.join(m)
    print(final_message)
    # print(starts + ' '+ message)


def get_all_files(mypath):
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    return onlyfiles


def is_contained(l, x):
    """

    :param l: list of strings
    :param x: major string
    :return: True if any of the elements in cluster is a contained in x
    """
    contained = False
    for y in l:
        if y in x:
            contained = True
    return contained


def list_to_str(lst, separator=',', rounding_decimals=None):
    if 'str' in str(type(lst)):
        return lst
    if 'float' in str(type(lst)) or 'int' in str(type(lst)):
        return str(lst)
    if lst is None or len(lst) == 0:
        return ''
    res = separator.join([fstr(x, rounding_decimals) for x in lst])
    return res


def read_bibtex_file(filename):
    try:
        with open(filename) as f:
            valid_lines = []
            for line in f:
                line = line.strip()
                if len(line) == 0:
                    continue
                llower = line.lower()
                if llower.startswith('month'):
                    continue
                if llower.startswith('doi'):
                    line = 'doi' + line[3:]  # so we're sure doi is in lower characters
                valid_lines.append(line)

        bibtex_str = '\n'.join(valid_lines)
        # bib_database = bibtexparser.load(f)
        bib_database = bibtexparser.loads(bibtex_str)
        return list(bib_database.entries)
    except Exception as ex:
        log_line(ex)
        return []


def tuple_to_str(tup, separator=','):
    return list_to_str(tup, separator)


def merge_data_labels(data_filename, labels_filename):
    data = open(data_filename)
    labels = open(labels_filename)
    labelps = open(data_filename.rstrip('.csv') + '_labels.csv', 'w')

    both_files = zip(data, labels)

    for data_line, labels_line in both_files:
        row_labels = labels_line.strip('\n\r')
        dl = data_line.strip('\n\r')
        labelps.write(dl + ',' + row_labels + '\n')
    labelps.close()
    data.close()
    labels.close()


def merge_data_labels_multi(data_filename, labels_filename):
    data = open(data_filename)
    labels = open(labels_filename)
    label1_writer = open(new_csv_file(data_filename + '_label1'), 'w')
    label2_writer = open(new_csv_file(data_filename + '_label2'), 'w')
    labelps_writer = open(new_csv_file(data_filename + '_labelps'), 'w')

    both_files = zip(data, labels)

    for data_line, labels_line in both_files:
        row_labels = labels_line.split(',')
        dl = data_line.strip('\n\r')
        label1_writer.write(dl + ',' + row_labels[0] + '\n')
        label2_writer.write(dl + ',' + row_labels[1] + '\n')
        label_ps = row_labels[0] + '+' + row_labels[1]
        labelps_writer.write(dl + ',' + label_ps + '\n')

    label1_writer.close()
    label2_writer.close()
    labelps_writer.close()


def new_csv_file(old_filename):
    return old_filename.rstrip('.csv').replace('0.', '') + '.csv'


def equal_core(text1, text2):
    """
    If true, the time series are measuring the same quantity so they can be subtracted.
    :param text1:
    :param text2:
    :return:
    """
    text1 = text1.lower()
    text2 = text2.lower()
    tx1 = text1.replace(' ', '_').replace('minimum', '').replace('maximum', '').replace('average', '').replace('mean',
                                                                                                               '').replace(
        'number', '').replace('total', '').replace('count', '').replace('avg',
                                                                        '').replace(
        'min', '').replace('max', '').replace('difference', '').replace('_in_', '').replace('_of_', '').replace('_', '')
    tx2 = text2.replace(' ', '_').replace('minimum', '').replace('maximum', '').replace('average', '').replace('mean',
                                                                                                               '').replace(
        'number', '').replace('total', '').replace('count', '').replace('avg',
                                                                        '').replace(
        'min', '').replace('max', '').replace('difference', '').replace('_in_', '').replace('_of_', '').replace('_', '')
    return tx1 == tx2


def common_filename(filenames, extension=None):
    if sum([1 if x == None else 0 for x in filenames]) > 0:
        return ''
    if len(filenames) == 0:
        return ''
    elif len(filenames) == 1:
        prefix = ''
    else:
        prefix = os.path.commonprefix(filenames)
    if extension is None:
        extension = filenames[0][filenames[0].rindex('.'):]
    combined_file = prefix
    i = 0
    for file in filenames:
        if file == '':
            # one of the files is empty so the result is also empty
            return ''
        part = file[len(prefix):]
        if '.' in part:
            part = part[:part.rindex('.')]
        if i > 0:
            combined_file += '_'
        combined_file += part
        i += 1
    if not combined_file.endswith(extension):
        combined_file += extension
    return combined_file


def merge_files(file_list, extension=None):
    if len(file_list) == 0:
        return None
    elif len(file_list) == 1:
        return file_list[0]
    else:
        common_file = common_filename(file_list, extension)
        with open(common_file, mode='w') as common:
            for file in file_list:
                with open(file) as lines:
                    for line in lines:
                        if not line.isspace():
                            common.write(line)
        return common_file


simpledec = re.compile(r"\d*\.\d+")
# decimal_format_string = "{:.5f}"
decimals = 5


# decimal_format_string = "{:." + str(decimals) + "f}"

def mround(match):
    # return decimal_format_string.format(float(match.group()))
    return str(round(float(match.group()), decimals))


def round_decimal_as_string(text, num_decimals):
    # decimal_format_string = "{:." + str(decimals) + "f}"
    decimals = num_decimals
    return re.sub(simpledec, mround, text)


# print(round_decimal_as_string('123456.123,1234.1234567,12,123.1', 2))


def simplify_name(name):
    simple_name = re.sub('[@:]+', '', name)
    simple_name = re.sub('[,; .\t\[\(\]\)-]+', '_', simple_name)
    return simple_name


def flatten_dict_arrays(key_values):
    flat_values = []
    for key in sorted(key_values):
        flat_values = np.hstack((flat_values, key_values[key]))

    return flat_values


def vstack_dict_arrays(original, new):
    for key in sorted(new):
        if key not in original:
            original = new
            break
        else:
            original[key] = np.vstack((original[key], new[key]))
    return original


def save_dict(all_data, filename, exceptions=None):
    """

    :param all_data:
    :param filename:
    :param exceptions: List of strings of the keys that should NOT be saved
    :return:
    """
    for key in all_data:
        if exceptions is not None and key in exceptions:
            continue
        current_filename = new_csv_file(filename + key)
        write_csv_file(all_data[key], current_filename)


def get_dummy_class1(label1_hierarchy, label2_hierarchy, label2):
    for key in sorted(label2_hierarchy[label2]):
        if label2_hierarchy[label2][key] == 0:
            return key


def get_dummy_class2(label1_hierarchy, label2_hierarchy, label1):
    for key in sorted(label1_hierarchy[label1]):
        if label1_hierarchy[label1][key] == 0:
            return key


def add_dummy_class1(label1_hierarchy, label2_hierarchy, label2_predictions):
    dummy_predictions = []
    for label2 in label2_predictions:
        label2 = label2[0]
        label1 = get_dummy_class1(label1_hierarchy, label2_hierarchy, label2)
        dummy_predictions.append(label1 + ',' + label2)
    return dummy_predictions


def add_dummy_class2(label1_hierarchy, label2_hierarchy, label1_predictions):
    dummy_predictions = []
    for label1 in label1_predictions:
        label1 = label1[0]
        label2 = get_dummy_class2(label1_hierarchy, label2_hierarchy, label1)
        dummy_predictions.append(label1 + ',' + label2)
    return dummy_predictions


def is_equal(a, b):
    c = []
    ids = []
    i = 0
    for v in a:
        if v in b:
            c.append(True)
            ids.append(i)
        else:
            c.append(False)
        i += 1

    return (c, ids)


def sdiv(a, b):
    try:
        return a * 1.0 / b
    except:
        return -1


email_reg = re.compile(r'([a-zA-Z0-9-_.]+@[a-zA-Z0-9-_.]+)', flags=re.IGNORECASE)


def extract_email(string):
    if is_empty(string):
        return ''
    m = email_reg.match(string)
    if m is None:
        return ''
    email = m.groups()[0]
    return email


def is_empty(x):
    return x is None or (is_str(x) and len(x.strip()) == 0)


def is_emptyz(x):
    return x is None or (is_str(x) and len(x.strip()) == 0) or str(x).strip() == '0'


def lsub(source, pattern, replacement=''):
    if source[:len(pattern)] == pattern:
        return replacement + source[len(pattern):]
    else:
        return source


def rsub(source, pattern, replacement=''):
    if source[-len(pattern):] == pattern:
        return source[:-len(pattern)] + replacement
    else:
        return source


def to_regex_pattern_simple(x):
    pat = re.compile(r'[^a-z0-9]+', flags=re.IGNORECASE)
    r = '^' + pat.sub('.*', x) + '$'
    return r


def to_regex_pattern(x):
    x_safe = x.replace(
        '\\', '\\\\').replace('.', '\.').replace('^', '\^').replace('$', '\$').replace('+', '\+').replace('?',
                                                                                                          '\?').replace(
        '(', '\(').replace(')', '\)').replace('[', '\[').replace(']', '\]').replace('{', '\{').replace('}',
                                                                                                       '\}').replace(
        '|', '\|')
    r = '^' + x_safe + '$'
    return r


def list_to_regex_pattern(l):
    if l is None:
        return None
    p = '|'.join([to_regex_pattern(x) for x in l])
    return p


#
#
# def read_csv_file_old(sql_filename, datatype='float'):
#     """
#     Compatible with python 2/3
#     :param sql_filename:
#     :param datatype:
#     :return:
#     """
#     log_line('Loading: ' + sql_filename)
#     values_list = []
#     with open(sql_filename, newline='') as f:
#         reader = csv.reader(f)
#         i = 0
#         for values_line in reader:
#             if i % 10000 == 0:
#                 log_line('Loading line:' + str(i))
#             i += 1
#             if datatype == 'float':
#                 values_line_f = list(map(float, values_line))
#                 values_list.append(values_line_f)
#             elif datatype == 'int':
#                 values_line_f = list(map(int, values_line))
#                 values_list.append(values_line_f)
#             else:
#                 values_list.append(values_line)
#     return values_list

def dt_to_epoch(dt=None, as_float=True):
    """
    Seconds from 1970-01-01.
    :param dt: the date as datetime object
    :return:
    """
    if dt is None:
        # dt = dt_tz(my_timezone='utc')
        return None
    dta = to_dt_tz_aware(dt)
    res = dta - RegexHolders.dt1970
    res = res.total_seconds()
    if as_float:
        return float(res)
    else:
        return res


def epoch_to_dt(epoch=0):
    milliseconds, seconds = math.modf(float(epoch))
    dt = datetime.datetime.utcfromtimestamp(seconds) + datetime.timedelta(milliseconds=milliseconds)
    dta = to_dt_tz_aware(dt)
    return dta


def read_file(filename):
    with open(filename, 'r', encoding='utf8') as f:
        s = f.read()
        return s


def move_file_or_folder(f, f_new):
    # Check if file already exists
    if not os.path.exists(f):
        log_line(f"Source path doesn't exist {f}. Cancelling!")
        return
    if os.path.isdir(f_new):
        log_line(f'Folder {f} exists in the destination path {f_new}. Will remove it first!')
        shutil.rmtree(f_new)

    elif os.path.isfile(f_new):
        log_line(f'File {f} exists in the destination path {f_new}. Will remove it first!')
        os.remove(f_new)

    dest = shutil.move(f, f_new)


def read_csv_file(filename, datatype=None, separate_header=False, retained_columns=None, separator='\t',
                  has_header=False, ignored_columns=set(), header_line_index=0):
    """

    :param filename: sourc
    :param datatype: int, str, float, line. If 'line' then the full lines are loaded as they are in string format
    :param separate_header:
    :param retained_columns:
    :param separator:
    :param has_header:
    :param ignored_columns:
    :param header_line_index: in which line is the header (1-based), relevant if has_header=True
    :return:
    """
    if separate_header:
        has_header = True
    log_line('Loading: ' + filename)
    values_list = []
    header = None

    with open(filename, newline='', encoding='utf8') as f:
        reader = csv.reader(f, delimiter=separator, quoting=csv.QUOTE_MINIMAL)
        i = 0
        first_line_index = header_line_index + 1
        for line in reader:
            i += 1
            if i % 10000 == 0:
                log_line('Loading line:' + str(i))
            if not line or i < header_line_index:
                continue
            if datatype == 'line':
                # Need to re-read line as text for this mode
                f.seek(0)
                for j, raw_line in enumerate(f):
                    if j + 1 == i:
                        if separate_header and i == header_line_index:
                            header = raw_line
                        else:
                            values_list.append(raw_line.strip())
                        break
                continue

            values = [v.strip() for v in line]
            values_line = []

            if i == header_line_index + 1 and has_header and separate_header:
                header = values
                first_line_index += 1
                continue

            if i == first_line_index:
                columns = len(values)
                if retained_columns is not None:
                    ignored_columns = set(
                        [k for k in range(columns) if k not in retained_columns or k in ignored_columns])
                if len(values) > 0 and datatype is None:
                    if is_int(values[-1]):
                        datatype = 'int'
                    elif is_float(values[-1]):
                        datatype = 'float'
                    else:
                        datatype = 'str'
                if datatype == 'int':
                    cfunc = int
                elif datatype == 'float':
                    cfunc = float
                else:
                    cfunc = str

            for j in range(len(values)):
                if j not in ignored_columns:
                    try:
                        tv = cfunc(values[j])
                    except:
                        cfunc = str
                        tv = cfunc(values[j])
                    values_line.append(tv)

            values_list.append(values_line)

    if separate_header and has_header:
        return values_list, header
    else:
        return values_list


def split_file_to_data_and_labels(filename, separator=','):
    """
    Split a CSV file that contains the whole dataset to 2 files: data and labels file.

    a,b,c,y -> data: a,b,c  label:y
    """
    data_filename = filename.replace('.csv', '') + '_data.csv'
    labels_filename = filename.replace('.csv', '') + '_labels.csv'
    pattern = '(.*)' + separator + '(.*)'
    regex = re.compile(pattern)
    with open(filename) as lines, open(data_filename, mode='w') as data_file, open(labels_filename,
                                                                                   mode='w') as labels_file:
        for line in lines:
            m = regex.match(line)
            data = m.groups()[0]
            label = m.groups()[1]
            data_file.write(data + '\n')
            labels_file.write(label + '\n')
    return data_filename, labels_filename


def split_file_randomly(src_file, fractions=[0.5, 0.5], separator=',', seed=None):
    """
    Random split a CSV file that contains the whole dataset to 2 or more files: data and labels file.

split_file_randomly('train_subjects.txt', [0.4, 0.3, 0.3])
    """
    filename = src_file.replace('.csv', '').replace('.txt', '')
    raw_data = read_csv_file(src_file, datatype='line')
    data = np.array(raw_data)
    import random
    random.seed(seed)
    line_ind = list(range(len(data)))
    random.shuffle(line_ind)
    i = 0
    prev_ind = 0
    for frac in fractions:
        i += 1
        filei = filename + '_' + str(i) + '_' + str(frac) + '.txt'
        if i == len(fractions):
            next_ind = len(data)
        else:
            cur_lines = int(len(data) * frac)
            next_ind = prev_ind + cur_lines
        indexes = line_ind[prev_ind: next_ind]
        datai = data[indexes]
        prev_ind = next_ind
        write_csv_file(datai, filei, separator)


def round_csv_file(filename, decimals):
    csv_data = read_csv_file(filename)
    dataset = np.array(csv_data)
    csv_data_rounded = np.around(dataset, decimals).tolist()
    new_filename = filename + '_rounded' + str(decimals) + '.csv'
    write_csv_file(csv_data_rounded, new_filename)
    return new_filename


def round_npdict(data, decimals):
    for key in data:
        data[key] = np.around(data[key], decimals)
    return data


def label_stats(labels_filename):
    labels = read_csv_file(labels_filename, datatype='str')
    label1_counts = {}

    for label in labels:
        label1_counts.setdefault(label[0], 0)

        label1_counts[label[0]] += 1

    n = float(len(labels))
    print('Label 1 combinations: ' + str(len(label1_counts)))
    print(json.dumps(label1_counts, indent=1, sort_keys=True))

    l1_lst = [(k, v, round(v / n, 3)) for k, v in label1_counts.items()]
    l1_lst_s = sorted(l1_lst, key=operator.itemgetter(1))

    out_file = new_csv_file(labels_filename + '_label1_counts')
    write_csv_file(l1_lst_s, out_file)

    return (label1_counts, out_file)


def labels_stats(labels_filename):
    labels = read_csv_file(labels_filename, datatype='str')
    label1_counts = {}
    label2_counts = {}
    labelps_counts = {}

    for label in labels:
        label1_counts.setdefault(label[0], 0)
        label2_counts.setdefault(label[1], 0)
        labelps_counts.setdefault(label[0] + '+' + label[1], 0)

        label1_counts[label[0]] += 1
        label2_counts[label[1]] += 1
        labelps_counts[label[0] + '+' + label[1]] += 1

    n = float(len(labels))
    print('Label 1 combinations: ' + str(len(label1_counts)))
    print(json.dumps(label1_counts, indent=1, sort_keys=True))

    print('Label 2 combinations: ' + str(len(labelps_counts)))
    print(json.dumps(label2_counts, indent=1, sort_keys=True))

    print('Label PS combinations: ' + str(len(labelps_counts)))
    print(json.dumps(labelps_counts, indent=1, sort_keys=True))

    l1_lst = [(k, v, round(v / n, 3)) for k, v in label1_counts.items()]
    l1_lst_s = sorted(l1_lst, key=operator.itemgetter(1))
    l2_lst = [(k, v, round(v / n, 3)) for k, v in label2_counts.items()]
    l2_lst_s = sorted(l2_lst, key=operator.itemgetter(1))
    lps_lst = [(k, v, round(v / n, 3)) for k, v in labelps_counts.items()]
    lps_lst_s = sorted(lps_lst, key=operator.itemgetter(1))

    write_csv_file(l1_lst_s, labels_filename + '_label1_counts.csv')
    write_csv_file(l2_lst_s, labels_filename + '_label2_counts.csv')
    write_csv_file(lps_lst_s, labels_filename + '_labelps_counts.csv')

    return [label1_counts, label2_counts, labelps_counts]


def compare_regex_results(values, pattern1, pattern2):
    r1 = re.compile(pattern1, re.IGNORECASE)
    r2 = re.compile(pattern2, re.IGNORECASE)
    matches1 = []
    matches2 = []
    for v in values:
        if r1.search(v):
            matches1.append(v)
        if r2.search(v):
            matches2.append(v)
    if len(matches1) != len(matches2):
        return False
    matches1.sort()
    matches2.sort()
    return matches1 == matches2


def evaluate_whitelist_blacklist(values, whitelist=None, blacklist=None, blacklist_priority=False):
    if whitelist is not None:
        whitelist_regex = re.compile(whitelist, flags=re.IGNORECASE)
    if blacklist is not None:
        blacklist_regex = re.compile(blacklist, flags=re.IGNORECASE)

    selected_values = set()
    blacklisted = set()
    not_whitelisted = set()
    blacklist_priority = blacklist_priority or whitelist is None

    for i in range(len(values)):
        feature_name = values[i]

        on_blacklist = False
        if blacklist is not None:
            matches1 = re.search(blacklist_regex, feature_name)
            if matches1:
                on_blacklist = True
            else:
                matches2 = re.search(blacklist_regex, simplify_name(feature_name))
                if matches1 or matches2:
                    on_blacklist = True

        if on_blacklist and blacklist_priority:
            blacklisted.add(feature_name)
            continue

        if whitelist is not None:
            matches1 = re.search(whitelist_regex, feature_name)
            matches2 = re.search(whitelist_regex, simplify_name(feature_name))
            if not matches1 and not matches2:
                not_whitelisted.add(feature_name)
                continue
                # else: it's on the whitelist, which has priority, so we keep it
        selected_values.add(feature_name)

    return sorted(selected_values)


def get_labels_stats(labels_filename):
    labels = read_csv_file(labels_filename, datatype='str')
    label1_counts = {}
    label2_counts = {}
    labelps_counts = {}

    label1_hierarchy = {}
    label2_hierarchy = {}
    for label in labels:
        label1_counts.setdefault(label[0], 0)
        label2_counts.setdefault(label[1], 0)
        labelps_counts.setdefault(label[0] + ',' + label[1], 0)

        label1_hierarchy.setdefault(label[0], {})
        label1_hierarchy[label[0]].setdefault(label[1], 0)
        label1_hierarchy[label[0]][label[1]] += 1
        label2_hierarchy.setdefault(label[1], {})
        label2_hierarchy[label[1]].setdefault(label[0], 0)
        label2_hierarchy[label[1]][label[0]] += 1

        label1_counts[label[0]] += 1
        label2_counts[label[1]] += 1
        labelps_counts[label[0] + ',' + label[1]] += 1

    for label1 in label1_hierarchy:
        for label2 in label2_counts:
            if label2 not in label1_hierarchy[label1]:
                label1_hierarchy[label1][label2] = 0
    for label2 in label2_hierarchy:
        for label1 in label1_counts:
            if label1 not in label2_hierarchy[label2]:
                label2_hierarchy[label2][label1] = 0

    n = float(len(labels))
    print('Label 1 combinations: ' + str(len(label1_counts)))
    print(json.dumps(label1_counts, indent=1, sort_keys=True))

    print('Label 2 combinations: ' + str(len(labelps_counts)))
    print(json.dumps(label2_counts, indent=1, sort_keys=True))

    print('Label PS combinations: ' + str(len(labelps_counts)))
    print(json.dumps(labelps_counts, indent=1, sort_keys=True))

    l1_lst = [(k, v, round(v / n, 3)) for k, v in label1_counts.items()]
    l1_lst_s = sorted(l1_lst, key=operator.itemgetter(1))
    l2_lst = [(k, v, round(v / n, 3)) for k, v in label2_counts.items()]
    l2_lst_s = sorted(l2_lst, key=operator.itemgetter(1))
    lps_lst = [(k, v, round(v / n, 3)) for k, v in labelps_counts.items()]
    lps_lst_s = sorted(lps_lst, key=operator.itemgetter(1))

    # write_csv_file(l1_lst_s, labels_filename+'_label1_counts.csv')
    # write_csv_file(l2_lst_s, labels_filename+'_label2_counts.csv')
    # write_csv_file(lps_lst_s, labels_filename+'_labelps_counts.csv')

    # return [label1_counts, label2_counts, labelps_counts]
    return [label1_hierarchy, label2_hierarchy]


def df_to_dict(df: pd.DataFrame, key_columns, value_column=None, summary_function='count'):
    """
    This functions convert dataframe to dictionary where keys and values are column values and uses keys based on
    the key columns provided.
    The type of the dictionary is based on the columns 'value_column' and 'summary_function'.
    If there is 'value_column' provided the values come from that column, otherwise the values are integer based on
    the summary function.
    :param df:
    :param key_columns:
    :param value_column:
    :param summary_function:
    :return:
    """

    # define the key type (element = one column, list = more columns)
    if type(key_columns) in [list, tuple]:
        if len(key_columns) == 0:
            raise Exception("Key column is empty.")
        elif len(key_columns) == 1:
            key_type = 'element'
        else:
            key_type = 'list'
    else:
        raise Exception("Attribute key_columns should be list")

    # generate the dictionary
    result = dict()
    for row in df.itertuples():

        if key_type == 'element':
            key = getattr(row, key_columns[0])
        else:
            temp_key = [getattr(row, column) for column in key_columns]
            key = tuple(temp_key)

        # values are based on summary function
        if value_column is None:
            if summary_function == 'count':
                result.setdefault(key, 0)
                result[key] += 1
            else:
                raise Exception("This operation is not supported yet.")
        # values are based on the value column
        else:
            result.setdefault(key, [])
            value = getattr(row, value_column)
            values = result[key]
            if value not in values:
                values.append(value)
            result[key] = values

    return result
