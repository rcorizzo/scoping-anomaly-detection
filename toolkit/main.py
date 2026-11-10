#!/usr/bin/env python3
import os
from datetime import timedelta

import getopt
import sys
import time

from help_tools import helpers as h
from help_tools.helpers import log_line
from core.meta_analysis import crawl_and_analyze
from visual.output_results import plot_all
from core.search_config import SearchConfig
from visual.postprocess_filtered_articles import process_and_plot_filtered_articles


def version():
    print('3.0')


def usage():
    print('Usage:')
    print(
        ' python3 main.py -f folder   OR'
        ' python3 main.py -g file')
    print()
    print('-h              Help')
    print('--help          Help')
    print('--pomos         Help')
    print('-v              Print version')
    print('--version       Print version')
    print(
        '-f              Folder for all results data (abs or relative path) or path to the pickle file for -a'
        ' (Default: None - user will be asked)')
    print(
        '--repo          Repository folder where all downloaded data is kept. Default:the parent of the results folder')
    print(
        '--post_process  Post process and export results and charts (Default: False)')
    print('-p              Plot results')
    print('--plot          Plot results')
    print('-g              File containing filtered articles to re-plot graphs and charts')
    print('--graph         File containing filtered articles to re-plot graphs and charts')
    print('--plot_type     Format of charts. pdf/png. Default: plot_type=pdf')
    print('-s              Start year (Default: current-9)')
    print('--start_year=X  Start year (Default: current-9)')
    print('-e              End year (Default: current')
    print('--end_year=Y    End year (Default: current)')
    print('--ieee          y/yes/n/no. Default: IEEE=no')
    print('--pubmed        PubMed: y/yes/n/no. Default: pubmed=no')
    print('--pmc           PubMedCentral: y/yes/n/no. Default: pmc=no')
    print('--springer      y/yes/n/no. Default: Springer=no')
    print('--acm           y/yes/n/no. Default: ACM=no')
    print('--relevant      Minimum relevant properties. Default: relevant=3')
    print('--process       Process everything from scratch. This is the default behavior')
    print('--add_lin_coef  Add linear coefficients to charts (y/yes/n/no). Default: add_lin_coef=no')
    print(
        '--capitalize    Capitalize the properties in the charts. E.g. AI will be capitalized to Ai; System Design'
        ' -> System design (y/yes/n/no). Default: capitalize=no')
    print('--stem          Stem properties and abstracts. (y/yes/n/no). Default: stem=yes')
    print(
        '--ask_to_replace  Whether to ask the user about confirmation to replace existing files'
        ' (y/n/yes/no/true/false/1/0). Default ask_to_replace=true')
    print('--multithread    Execute analysis with multiple threads')
    print('--delete_caching Delete previously cached results')


def main(argv):
    t0 = time.time()
    log_line('Arguments:', argv)
    try:
        opts, args = getopt.getopt(argv, 'hvf:rps:e:g:',
                                   ['help', 'pomos', 'version', 'post_process', 'plot', 'plot_type=', "graph=",
                                    'pmc=', 'pubmed=', 'ieee=', 'springer=', 'capitalize=', 'acm=', 'start_year=',
                                    'end_year=', 'repo=', 'relevant=', 'ask_to_replace=',
                                    'add_lin_coef=', 'stem=', 'multithread=', 'delete_cache'])

        log_line('Parsed arguments:', opts)
    except Exception as e:
        log_line('Exception:', e)
        usage()
        sys.exit(2)
    post = None
    path = None
    graph_filepath = None
    pmc = None
    pubmed = None
    ieee = None
    springer = None
    acm = None
    start_year = None
    end_year = None
    plot = False
    plot_type = 'pdf'
    folder_repo = None
    relevant = None
    add_lin_coef = None
    stem = True
    capitalize = None
    multithread = True
    delete_cache = False
    for opt, arg in opts:
        try:
            if opt in ('-h', '--help', '--pomos'):
                usage()
                sys.exit()
            elif opt in ('-v', '--version'):
                version()
                sys.exit()
            elif opt in ('-f',):
                path = arg
            elif opt in ('-g',):
                graph_filepath = arg
            elif opt in ('--post_process',):
                post = True
            elif opt in ('--plot', '-p'):
                plot = True
            elif opt in ('--plot_type',):
                plot_type = 'png' if 'png' in arg.lower() else 'pdf'
            elif opt in ('--start_year', '-s'):
                start_year = int(arg)
            elif opt.lower() in ('--repo',):
                folder_repo = arg
            elif opt in ('--end_year', '-e'):
                end_year = int(arg)
            elif opt.lower() in ('--pubmed',):
                pubmed = 'n' not in arg.lower()
            elif opt.lower() in ('--capitalize',):
                capitalize = 'n' not in arg.lower()
            elif opt.lower() in ('--pmc',):
                pmc = 'n' not in arg.lower()
            elif opt.lower() in ('--ieee',):
                ieee = 'n' not in arg.lower()
            elif opt.lower() in ('--springer',):
                springer = 'n' not in arg.lower()
            elif opt.lower() in ('--acm',):
                acm = 'n' not in arg.lower()
            elif opt.lower() in ('--stem',):
                stem = 'n' not in arg.lower()
            elif opt.lower() in ('--relevant',):
                relevant = int(arg)
            elif opt.lower() in ('--add_lin_coef',):
                add_lin_coef = arg.lower() in ('yes', 'true', 'y', '1')
            elif opt.lower() in ('--ask_to_replace',):
                ask_to_replace = arg.lower() not in ('no', 'false', '0', 'n')
            elif opt.lower() in ('--multithread',):
                multithread = arg.lower() not in ('no', 'false', '0', 'n')
            elif opt.lower() in ('--delete_cache',):
                delete_cache = True
        except Exception as e:
            log_line('Exception:', opt, arg, e)
    if path is not None:
        if os.path.isfile(path):
            folder = h.get_parent_folder(path)
            filename = path
        else:
            folder = path.rstrip('/\\')
            filename = os.path.join(path, 'search_data.json')
        folder = folder.rstrip('/\\')
    else:
        filename, folder = None, None
    h.log_line('Plot:', plot, 'Plot type:', plot_type)

    main_parsed(filename, folder, ieee=ieee, pmc=pmc, pubmed=pubmed, springer=springer, acm=acm,
                graph_filepath=graph_filepath, folder_repo=folder_repo, relevant=relevant, add_lin_coef=add_lin_coef,
                plot_type=plot_type, capitalize=capitalize, stem=stem,
                start_year=start_year, end_year=end_year, post=post, plot=plot, multithread=multithread,
                delete_cache=delete_cache)
    dur = (time.time() - t0)
    dur_ts = timedelta(seconds=dur)
    h.log_line('Done. Duration:', dur_ts, 'Duration in seconds:', dur)


def main_parsed(filename, folder, ieee=None, pmc=None, pubmed=None, springer=None, acm=None,
                graph_filepath=None, folder_repo=None, relevant=None, add_lin_coef=None, plot_type=None,
                capitalize=None, stem=None, start_year=None, end_year=None, post=False, plot=False, multithread=False,
                delete_cache=False):
    search = None
    if filename is not None:
        search = SearchConfig.prepare_search_object(
            filename, ieee=ieee, pmc=pmc, pubmed=pubmed, springer=springer, acm=acm, folder_repo=folder_repo,
            relevant=relevant, add_lin_coef=add_lin_coef, plot_type=plot_type, capitalize=capitalize, stem=stem,
            start_year=start_year, end_year=end_year, multithread=multithread, delete_cache=delete_cache)

    if post and graph_filepath is not None:
        process_and_plot_filtered_articles(filtered_articles_filename=graph_filepath, search_obj=search,
                                           add_lin_coef=add_lin_coef, extension=plot_type, capitalize=capitalize)
    elif post:
        crawl_and_analyze(search, file_manually_filtered_articles=graph_filepath)
    elif plot:
        plot_all(search)
    else:
        crawl_and_analyze(search, file_manually_filtered_articles=graph_filepath)

    h.safe_exec_bash_cmd(['bash', '/mnt/sda/article-analysis/bash_scripts/commit_results_specific.sh', folder])


if __name__ == "__main__":
    main(sys.argv[1:])
