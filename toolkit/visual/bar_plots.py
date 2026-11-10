import math

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import LogFormatter
from slugify import slugify

from configuration.config import Config
from help_tools import helpers as h
from help_tools.tools import tools

matplotlib.use('Agg')


def plot_year(src_filename, dest_filename=None, add_lin_coef=True, plot_type='pdf', capitalize=False, **kwargs):
    try:
        df = pd.read_csv(src_filename, index_col='year', sep='\t')
        # df1.columns = [x.replace('_', ' ') for x in df1.columns]
        if add_lin_coef:
            tools.add_lin_coef_to_df_name(df)
        # https://stackoverflow.com/questions/25447700/annotate-bars-with-values-on-pandas-bar-plots
        # matplotlib.rcParams.update(matplotlib.rcParamsDefault)
        # print(matplotlib.rcParamsDefault['figure.figsize'])
        width = 6.4
        num_years = len(df.index)
        if num_years >= 20:
            width *= 2
        matplotlib.rcParams['figure.figsize'] = [width, 4.8]
        # matplotlib.style.use('tableau-colorblind10')
        # matplotlib.style.use('default')
        rotation = 0
        if num_years > 11:
            rotation = 45
        if capitalize:
            df.columns = [x.replace('_', ' ').capitalize() for x in df.columns]
        else:
            df.columns = [x.replace('_', ' ') for x in df.columns]
        ax = df.plot.bar(rot=rotation, fontsize=10, align='center')
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: h.fmt_number(x)))
        ax.yaxis.grid(linestyle='dotted')
        bottom, top = plt.ylim()
        plt.ylim(top=top * 1.07)
        # Add labels to the plot
        # https://matplotlib.org/2.0.2/examples/color/named_colors.html
        _add_labels(ax, df)

        ax.set_ylabel('Number of articles')
        ax.set_xlabel('Year')
        _add_legend(ax, df, rotation=rotation)
        if dest_filename is None:
            dest_filename = h.remove_extension(src_filename).replace('_pivot', '') + '.' + plot_type
        dpi = 300 if plot_type == 'png' else None
        ax.get_figure().savefig(dest_filename, bbox_inches='tight', dpi=dpi)
        if plot_type != 'pdf':
            ax.get_figure().savefig(h.remove_extension(dest_filename) + '.pdf', bbox_inches='tight')
    except Exception as e:
        h.log_line('Error plotting:', src_filename, e)
    plt.close('all')


def plot_source(src_filename, dest_filename=None, plot_type='pdf', capitalize=False, **kwargs):
    try:
        df = pd.read_csv(src_filename, index_col='source', sep='\t')
        # make sure numbers add up
        df = df[df[Config.PRISMA_considered] > 0]
        # df[Config.PRISMA_incomplete_data] = df[Config.PRISMA_considered] - df[Config.PRISMA_invalid_years] - df[Config.PRISMA_duplicates] - df[Config.PRISMA_remaining]
        if capitalize:
            df.columns = [x.replace('_', ' ').capitalize() for x in df.columns]
        else:
            df.columns = [x.replace('_', ' ') for x in df.columns]
        df.index = df.index.str.replace('NCBI:', '')
        df.sort_index(inplace=True)
        matplotlib.rcParams['figure.figsize'] = [12.8, 4.8]
        ax = df.plot.bar(rot=0, fontsize=10, align='center')
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: h.fmt_number(x)))
        ax.yaxis.grid(linestyle='dotted')
        _add_labels(ax, df)
        bottom, top = plt.ylim()
        plt.ylim(top=top * 1.07)
        ax.set_ylabel('Number of articles')
        ax.set_xlabel('Digital library')
        _add_legend(ax, df)
        if dest_filename is None:
            dest_filename = h.remove_extension(src_filename).replace('_pivot', '') + '.' + plot_type
        dpi = 300 if plot_type == 'png' else None
        ax.get_figure().savefig(dest_filename, bbox_inches='tight', dpi=dpi)
        if plot_type != 'pdf':
            ax.get_figure().savefig(h.remove_extension(dest_filename) + '.pdf', bbox_inches='tight')
    except Exception as e:
        h.log_line('Error plotting:', src_filename, e)
    plt.close('all')


def plot_year_property_group(src_filename, dest_filename=None, add_lin_coef=True, plot_type='pdf', capitalize=False,
                             **kwargs):
    try:
        df = pd.read_csv(src_filename, sep='\t', index_col='property_group')
        df = df.T
        fig_width = 6.4
        horz_stretch = 1.0
        num_years = len(df.index)
        if len(df.columns) > 3 or num_years >= 20:
            horz_stretch = 2.0
        fig_width = int(fig_width * horz_stretch)

        rotation = 0

        if (num_years > 11 and horz_stretch < 2) or num_years >= 20:
            rotation = 45
        if add_lin_coef:
            tools.add_lin_coef_to_df_name(df)

        matplotlib.rcParams['figure.figsize'] = [fig_width, 4.8]
        if capitalize:
            df.columns = [x.replace('_', ' ').capitalize() for x in df.columns]
        else:
            df.columns = [x.replace('_', ' ') for x in df.columns]
        ax = df.plot.bar(rot=rotation, align='center', fontsize=10)
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: h.fmt_number(x)))
        ax.yaxis.grid(linestyle='dotted')
        ax.set_ylabel('Number of relevant articles')
        ax.set_xlabel('Year')
        bottom, top = plt.ylim()
        plt.ylim(top=top * 1.07)
        _add_labels(ax, df)
        _add_legend(ax, df, rotation=rotation)
        if dest_filename is None:
            dest_filename = h.remove_extension(src_filename).replace('_pivot', '') + '.' + plot_type
        dpi = 300 if plot_type == 'png' else None
        ax.get_figure().savefig(dest_filename, bbox_inches='tight', dpi=dpi)
        if plot_type != 'pdf':
            ax.get_figure().savefig(h.remove_extension(dest_filename) + '.pdf', bbox_inches='tight')
    except Exception as e:
        h.log_line('Error plotting:', src_filename, e)
    plt.close('all')


def plot_year_source(src_filename, dest_filename=None, add_lin_coef=True, plot_type='pdf', capitalize=False, **kwargs):
    try:
        df = pd.read_csv(src_filename, sep='\t', index_col='source')
        df.index = df.index.str.replace('NCBI:', '')
        df = df.T
        df = df.reindex(sorted(df.columns), axis=1)
        df.sort_index(inplace=True)
        if add_lin_coef:
            tools.add_lin_coef_to_df_name(df)
        fig_width = 6.4
        horz_stretch = 1.0
        num_years = len(df.index)
        if len(df.columns) > 3 or num_years >= 20:
            horz_stretch = 2.0
        fig_width = int(fig_width * horz_stretch)

        rotation = 0
        if (num_years > 11 and horz_stretch < 2) or (horz_stretch >= 2 and num_years >= 20):
            rotation = 45
        matplotlib.rcParams['figure.figsize'] = [fig_width, 4.8]
        ax = df.plot.bar(rot=rotation, align='center', fontsize=10)
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: h.fmt_number(x)))
        ax.yaxis.grid(linestyle='dotted')
        ax.set_ylabel('Number of relevant articles')
        ax.set_xlabel('Year')
        bottom, top = plt.ylim()
        plt.ylim(top=top * 1.07)
        _add_labels(ax, df)
        _add_legend(ax, df, rotation=rotation)
        if dest_filename is None:
            dest_filename = h.remove_extension(src_filename).replace('_pivot', '') + '.' + plot_type
        dpi = 300 if plot_type == 'png' else None
        ax.get_figure().savefig(dest_filename, bbox_inches='tight', dpi=dpi)
        if plot_type != 'pdf':
            ax.get_figure().savefig(h.remove_extension(dest_filename) + '.pdf', bbox_inches='tight')
    except Exception as e:
        h.log_line('Error plotting:', src_filename, e)
    plt.close('all')


def plot_keyword_source(src_filename, dest_filename=None, plot_type='pdf', capitalize=False, **kwargs):
    try:
        df = pd.read_csv(src_filename, sep='\t', index_col='keyword')
        df.columns = [c.replace('NCBI:', '') for c in df.columns]
        df = df.T
        df = df.reindex(sorted(df.columns), axis=1)
        df.sort_index(inplace=True)
        fig_width = 6.4
        horz_stretch = 1.0
        if len(df.columns) > 3:
            horz_stretch = 2.0
        fig_width = int(fig_width * horz_stretch)

        matplotlib.rcParams['figure.figsize'] = [fig_width, 4.8]
        ax = df.plot.bar(rot=0, align='center', fontsize=10)
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: h.fmt_number(x)))
        ax.yaxis.grid(linestyle='dotted')
        ax.set_ylabel('Number of relevant articles')
        ax.set_xlabel('Source')
        bottom, top = plt.ylim()
        plt.ylim(top=top * 1.07)
        _add_labels(ax, df)
        _add_legend(ax, df)
        if dest_filename is None:
            dest_filename = h.remove_extension(src_filename).replace('_pivot', '') + '.' + plot_type
        dpi = 300 if plot_type == 'png' else None
        ax.get_figure().savefig(dest_filename, bbox_inches='tight', dpi=dpi)
        if plot_type != 'pdf':
            ax.get_figure().savefig(h.remove_extension(dest_filename) + '.pdf', bbox_inches='tight')
    except Exception as e:
        h.log_line('Error plotting:', src_filename, e)
    plt.clf()


def plot_year_keyword(src_filename, dest_filename=None, add_lin_coef=True, plot_type='pdf', capitalize=False, **kwargs):
    try:
        df = pd.read_csv(src_filename, sep='\t', index_col='keyword')
        df = df.T
        df = df.reindex(sorted(df.columns), axis=1)
        df.sort_index(inplace=True)
        if add_lin_coef:
            tools.add_lin_coef_to_df_name(df)
        num_years = len(df.index)
        rotation = 0
        fig_width = 6.4
        horz_stretch = 1.0
        if len(df.columns) > 3 or num_years >= 20:
            horz_stretch = 2.0
        fig_width = int(fig_width * horz_stretch)

        if (num_years > 11 and horz_stretch < 2) or (horz_stretch >= 2 and num_years >= 20):
            rotation = 45

        matplotlib.rcParams['figure.figsize'] = [fig_width, 4.8]
        ax = df.plot.bar(rot=rotation, align='center', fontsize=10)
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: h.fmt_number(x)))
        ax.yaxis.grid(linestyle='dotted')
        ax.set_ylabel('Number of relevant articles')
        ax.set_xlabel('Year')
        bottom, top = plt.ylim()
        plt.ylim(top=top * 1.07)
        _add_labels(ax, df)
        _add_legend(ax, df, rotation)
        if dest_filename is None:
            dest_filename = h.remove_extension(src_filename).replace('_pivot', '') + '.' + plot_type
        dpi = 300 if plot_type == 'png' else None
        ax.get_figure().savefig(dest_filename, bbox_inches='tight', dpi=dpi)
        if plot_type != 'pdf':
            ax.get_figure().savefig(h.remove_extension(dest_filename) + '.pdf', bbox_inches='tight')
    except Exception as e:
        h.log_line('Error plotting:', src_filename, e)
    plt.close('all')


def plot_year_property(src_filename: str, dest_filename: str = None, add_lin_coef=True, plot_type='pdf',
                       capitalize=False, **kwargs):
    """
    Generates a separate chart for each property.
    :param src_filename:
    :param dest_filename: If None, it will be generated from ```src_filename```.
    :return:
    """
    try:
        df = pd.read_csv(src_filename, sep='\t', index_col=None)
        property_groups = sorted(set(df['property_group'].values))
        if dest_filename:
            dest_filename = h.remove_extension(dest_filename).replace('_pivot', '')
        else:
            dest_filename = h.remove_extension(src_filename).replace('_pivot', '')
        dpi = 300 if plot_type == 'png' else None
        for prop_gr in property_groups:
            cdf = df[df['property_group'] == prop_gr]
            cdf = cdf.drop('property_group', axis=1)
            cdf.set_index('property', inplace=True)
            cdf = cdf.T
            if add_lin_coef:
                tools.add_lin_coef_to_df_name(cdf)
            fig_width = 6.4
            horz_stretch = 1.0
            num_years = len(cdf.index)
            rotation = 0
            if len(cdf.columns) > 3 or num_years >= 20:
                horz_stretch = 2.0
            if (num_years > 11 and horz_stretch < 2) or (horz_stretch >= 2 and num_years >= 20):
                rotation = 45
            fig_width = int(fig_width * horz_stretch)

            matplotlib.rcParams['figure.figsize'] = [fig_width, 4.8]
            if capitalize:
                cdf.columns = [x.replace('_', ' ').capitalize() for x in cdf.columns]
            else:
                cdf.columns = [x.replace('_', ' ') for x in cdf.columns]
            ax = cdf.plot.bar(rot=rotation, align='center', fontsize=10)
            ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: h.fmt_number(x)))
            ax.yaxis.grid(linestyle='dotted')
            ax.set_ylabel('Number of relevant articles')
            ax.set_xlabel('Year')
            bottom, top = plt.ylim()
            plt.ylim(top=top * 1.07)
            ax.set_title(prop_gr)
            _add_labels(ax, cdf)
            _add_legend(ax, cdf, rotation=rotation)
            cdest_filename = dest_filename.replace('_pivot', '') + '_' + slugify(prop_gr) + '.' + plot_type
            h.log_line('plotting to', cdest_filename)
            ax.get_figure().savefig(cdest_filename, bbox_inches='tight', dpi=dpi)
            if plot_type != 'pdf':
                ax.get_figure().savefig(h.remove_extension(cdest_filename) + '.pdf', bbox_inches='tight')
    except Exception as e:
        h.log_line('Error plotting:', src_filename, e)
    plt.close('all')


def plot_property_group_percentage(src_filename: str, dest_filename: str = None, add_lin_coef=True, plot_type='pdf', max_len=20,
                                   capitalize=False, **kwargs):
    try:
        df = pd.read_csv(src_filename, sep='\t', index_col=None)
        property_groups = sorted(set(df['property_group'].values))
        if dest_filename:
            dest_filename = h.remove_extension(dest_filename)
        else:
            dest_filename = h.remove_extension(src_filename)
        for prop_gr in property_groups:
            cdf = df[df['property_group'] == prop_gr]
            cdf = cdf.drop('property_group', axis=1)
            bars_raw = cdf['property'].tolist()
            bars = []
            for bar in bars_raw:
                if isinstance(bar, str):
                    if len(bar) > max_len:
                        bars.append(bar[:max_len] + "...")
                    else:
                        bars.append(bar)
                else:
                    # NaN values
                    bars.append("")
            if len(bars) <= 5:
                bar_height = 0.5
                figsize_x = 37
                figsize_y = 27
            elif 5 < len(bars) < 13:
                bar_height = 0.3
                figsize_x = 47
                figsize_y = 37
            else:
                bar_height = 0.1
                figsize_x = 57
                figsize_y = 67
            height = cdf['cnt']
            percentage = cdf['percentage'].tolist()
            values_perc = []
            heights = height.tolist()

            for i in range(len(height)):
                val_str = str(heights[i]) + "   (" + str('{:.2%}'.format(percentage[i])) + ")"
                values_perc.append(val_str)
            y_pos = np.arange(len(bars))
            plt.clf()
            plt.figure(figsize=(figsize_x, figsize_y))
            plt.rcParams.update({'font.size': 22})
            plt.barh(y_pos, height, height=bar_height)
            plt.grid(linestyle='dotted', axis='x')
            plt.yticks(y_pos, bars)
            locs, labels = plt.yticks()
            left, right = plt.xlim()
            text_alignment_x = right / 24
            plt.xlim(right=right * 1.07)
            for bar in range(len(bars)):
                plt.text(text_alignment_x + heights[bar], locs[bar], values_perc[bar], va='center', ha='center')
            # plt.yticks(y_pos, bars)
            plt.xlabel('Number of articles', fontsize=25)
            plt.ylabel('Property', fontsize=25)
            plt.title(prop_gr, fontsize=30)
            dest = dest_filename + '_' + slugify(prop_gr) + '.' + plot_type
            plt.savefig(dest, format='pdf')
    except Exception as e:
        h.log_line('Error plotting:', src_filename, e)
    plt.close()


def _add_labels(ax, df: pd.DataFrame, rotation=90):
    """
    Adds labels to each rectangle in a bar plot
    :param ax: matplotlib.axes.Axes object
    :param df:
    :return:
    """
    size_dict = {1: 8, 2: 8, 3: 7, 4: 7, 5: 7, 6: 6, 7: 6, 8: 5}
    size = size_dict.get(len(df.columns), 4.5)
    style = dict(size=size, color='black', rotation=rotation)
    x_offset = ax.patches[0].get_width() / 2.0
    # max_height = for p in ax.patches
    for i, p in enumerate(ax.patches):
        if rotation == 90:
            ax.annotate(h.fmt_number(p.get_height()), (p.get_x() + x_offset, p.get_height()),
                        verticalalignment='bottom', horizontalalignment='center', **style)
        else:
            ax.annotate(h.fmt_number(p.get_height()), (p.get_x() + x_offset, p.get_height() * 1.015), ha='center',
                        **style)


def _add_legend(ax, df: pd.DataFrame, rotation=0):
    """
    Adds legend below the bar chart
    :param ax:
    :param df:
    :param 0:
    :return:
    """
    legend_max_chars = 7 * 10 + 64  # 7 labels*10 + 64 chars
    # legend_max_chars = min(64, int(46 * horz_stretch))  # empirically 46 chars for plot with width=6.4 and font=10
    col_lens = [len(cn) for cn in df.columns]
    legend_len = sum(col_lens) + 10 * len(df.columns)
    legend_cols = len(df.columns)
    while legend_cols > 1 and legend_len > legend_max_chars:
        legend_cols = int(min(math.ceil(legend_cols / 2.0), legend_cols - 1))
        legend_len = 0
        for bucket in range(legend_cols):
            bucket_cols = col_lens[bucket * legend_cols:(bucket + 1) * legend_cols]
            bucket_len = sum(bucket_cols) + 10 * len(bucket_cols)
            legend_len = max(legend_len, bucket_len)
    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=len(y.columns), fancybox=True, shadow=True)
    if rotation == 0:
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=legend_cols, frameon=False, shadow=True)
    elif rotation == 45:
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=legend_cols, frameon=False, shadow=True)
    else:
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=legend_cols, frameon=False, shadow=True)
