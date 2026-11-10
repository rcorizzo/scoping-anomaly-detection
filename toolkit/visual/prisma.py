import matplotlib
import matplotlib.patches as mpatch
import matplotlib.pyplot as plt
import pandas as pd

from configuration.config import Config
from help_tools import helpers as h

matplotlib.use('Agg')

from core.search_config import SearchConfig

def generate_prisma_output(src_filename: str, dest_filename: str, identified_other: int, skipped_other: int,
                           invalid_years: int, duplicates_removed: int, considered: int, relevant: int, selected: int):
    # Prepare stats for the PRISMA chart

    df = pd.read_excel(src_filename, engine='openpyxl')
    # TODO: should we include the parsing errors somewhere?
    parsing_errors = int(df[Config.PRISMA_parsing_errors].sum())
    qualitative_synthesis = relevant
    quantitative_synthesis = selected
    if quantitative_synthesis == 0:
        quantitative_synthesis = qualitative_synthesis
    prisma_stats = dict()
    prisma_stats['identified_database'] = considered
    prisma_stats['identified_other'] = identified_other
    prisma_stats['_duplicates'] = duplicates_removed
    prisma_stats['_invalid_years'] = invalid_years
    prisma_stats['_incomplete_data'] = skipped_other
    prisma_stats['qualitative_synthesis'] = qualitative_synthesis
    prisma_stats['quantitative_synthesis'] = quantitative_synthesis

    prisma_stats['after_duplicates_removed'] = prisma_stats['identified_database'] + prisma_stats[
        'identified_other'] - prisma_stats['_duplicates']
    prisma_stats['records_screened'] = prisma_stats['after_duplicates_removed']
    prisma_stats['records_screened_excluded'] = prisma_stats['_invalid_years'] + prisma_stats['_incomplete_data']
    prisma_stats['assessed_eligibility'] = prisma_stats['records_screened'] - prisma_stats['records_screened_excluded']
    prisma_stats['assessed_eligibility_excluded'] = prisma_stats['assessed_eligibility'] - prisma_stats[
        'quantitative_synthesis']
    prisma_stats['assessed_eligibility_excluded'] = prisma_stats['assessed_eligibility'] - prisma_stats[
        'qualitative_synthesis']
    df_prisma_stats = pd.DataFrame(list(prisma_stats.items()), columns=['metric', 'count'])
    df_prisma_stats.to_csv(dest_filename, index=False, sep='\t')
    h.csv_to_excel(dest_filename)


def generate_prisma_plots(input_file: str, plot_type='pdf', **kwargs):
    plot_prisma(input_file, plot_type=plot_type)
    plot_prisma_scoping(input_file, plot_type=plot_type)


def plot_prisma_scoping(src_filename, dest_filename=None, plot_type='pdf', **kwargs):
    if not dest_filename:
        dest_filename = h.remove_extension(src_filename).replace('_pivot', '') + '_scoping.' + plot_type
    df = pd.read_excel(src_filename, header=0, engine='openpyxl')
    d = dict(list(zip(df['metric'].tolist(), df['count'].tolist())))
    try:
        if int(d['quantitative_synthesis']) > 0:
            d['quantitative_synthesis'] = int(d['quantitative_synthesis'])
    except:
        d['quantitative_synthesis'] = 'n/a'
    # https://matplotlib.org/examples/color/named_colors.html
    # https://stackoverflow.com/questions/14531346/how-to-add-a-text-into-a-rectangle
    fig, ax = plt.subplots()
    left_rectangles = {
        'Identification': mpatch.Rectangle((0, 18.5), 1, 5, facecolor='skyblue', edgecolor='black', linewidth=0.5),
        'Screening': mpatch.Rectangle((2, 11.5), 1, 6, facecolor='lightskyblue', edgecolor='black', linewidth=0.5),
        'Eligibility': mpatch.Rectangle((2, 6), 1, 4, facecolor='lightskyblue', edgecolor='black', linewidth=0.5),
        'Selection': mpatch.Rectangle((0, 6), 1, 11.5, facecolor='skyblue', edgecolor='black', linewidth=0.5),
        'Included': mpatch.Rectangle((0, 1), 1, 4, facecolor='skyblue', edgecolor='black', linewidth=0.5)}

    for r_text, r in left_rectangles.items():
        ax.add_artist(r)
        rx, ry = r.get_xy()
        cx = rx + r.get_width() / 2.0
        cy = ry + r.get_height() / 2.0
        ax.annotate(r_text, (cx, cy), color='black', weight='bold',
                    fontsize=4, verticalalignment='center', horizontalalignment='center', rotation=90)
    rnames = dict()
    rnames[1] = 'Records identified through\ndatabase searching\n(n=%s)' % h.fmt_number(d['identified_database'])
    rnames[2] = 'Additional records identified\nthrough other sources\n(n=%s)' % h.fmt_number(d['identified_other'])
    rnames[3] = 'Records after duplicates removed\n(n=%s)' % h.fmt_number(d['after_duplicates_removed'])
    rnames[4] = 'Records screened\n(n=%s)' % h.fmt_number(d['records_screened'])
    rnames[5] = 'Records excluded\n(n=%s)' % h.fmt_number(d['records_screened_excluded'])
    rnames[6] = "Articles' abstracts assessed\nfor eligibility\n(n=%s)" % h.fmt_number(d['assessed_eligibility'])
    rnames[7] = 'Articles excluded,\nwith reasons\n(n=%s)' % h.fmt_number(
        d['assessed_eligibility_excluded'])
    rnames[8] = 'Studies included in\ncollating and summarizing results\n(n=%s)' % h.fmt_number(
        d['qualitative_synthesis'])

    other_rectangles = {
        rnames[1]: mpatch.Rectangle((3, 19.5), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[2]: mpatch.Rectangle((13, 19.5), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[3]: mpatch.Rectangle((7, 15.5), 10, 2, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[4]: mpatch.Rectangle((8, 11.5), 8, 2, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[5]: mpatch.Rectangle((18, 11.5), 8, 2, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[6]: mpatch.Rectangle((8, 6.5), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[7]: mpatch.Rectangle((18, 6.5), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[8]: mpatch.Rectangle((8, 1.5), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5),
    }

    for r_text, r in other_rectangles.items():
        ax.add_artist(r)
        rx, ry = r.get_xy()
        cx = rx + r.get_width() / 2.0
        cy = ry + r.get_height() / 2.0

        ax.annotate(r_text, (cx, cy), color='black',
                    fontsize=4, verticalalignment='center', horizontalalignment='center', rotation=0)

    plt.arrow(x=9, y=19.5, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=15, y=19.5, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=12, y=15.5, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=12, y=11.5, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=12, y=6.5, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    # plt.arrow(x=12, y=6, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=16, y=12.5, dx=1.75, dy=0, head_width=0.1, linewidth=0.5)
    plt.arrow(x=16, y=8, dx=1.75, dy=0, head_width=0.1, linewidth=0.5)

    ax.set_xlim((-0.5, 27))
    ax.set_ylim((0.5, 24))
    ax.set_aspect('equal')

    fig.frameon = False
    ax.set_axis_off()
    dpi = 300 if plot_type == 'png' else None
    plt.savefig(dest_filename, bbox_inches='tight', dpi=dpi)
    if plot_type != 'pdf':
        plt.savefig(h.remove_extension(dest_filename) + '.pdf', bbox_inches='tight')


def plot_prisma(src_filename, dest_filename=None, plot_type='pdf', **kwargs):
    if not dest_filename:
        dest_filename = h.remove_extension(src_filename).replace('_pivot', '') + '.' + plot_type
    df = pd.read_excel(src_filename, header=0, engine='openpyxl')
    d = dict(list(zip(df['metric'].tolist(), df['count'].tolist())))
    try:
        if int(d['quantitative_synthesis']) > 0:
            d['quantitative_synthesis'] = int(d['quantitative_synthesis'])
    except:
        d['quantitative_synthesis'] = 'n/a'
    # https://matplotlib.org/examples/color/named_colors.html
    # https://stackoverflow.com/questions/14531346/how-to-add-a-text-into-a-rectangle
    fig, ax = plt.subplots()
    left_rectangles = {
        'Identification': mpatch.Rectangle((0, 22), 1, 6, facecolor='skyblue', edgecolor='black', linewidth=0.5),
        'Screening': mpatch.Rectangle((0, 15), 1, 6, facecolor='skyblue', edgecolor='black', linewidth=0.5),
        'Eligibility': mpatch.Rectangle((0, 8), 1, 6, facecolor='skyblue', edgecolor='black', linewidth=0.5),
        'Included': mpatch.Rectangle((0, 1), 1, 6, facecolor='skyblue', edgecolor='black', linewidth=0.5)}

    for r_text, r in left_rectangles.items():
        ax.add_artist(r)
        rx, ry = r.get_xy()
        cx = rx + r.get_width() / 2.0
        cy = ry + r.get_height() / 2.0
        ax.annotate(r_text, (cx, cy), color='black', weight='bold',
                    fontsize=4, verticalalignment='center', horizontalalignment='center', rotation=90)
    rnames = dict()
    rnames[1] = 'Records identified through\ndatabase searching\n(n=%s)' % h.fmt_number(d['identified_database'])
    rnames[2] = 'Additional records identified\nthrough other sources\n(n=%s)' % h.fmt_number(d['identified_other'])
    rnames[3] = 'Records after duplicates removed\n(n=%s)' % h.fmt_number(d['after_duplicates_removed'])
    rnames[4] = 'Records screened\n(n=%s)' % h.fmt_number(d['records_screened'])
    rnames[5] = 'Records excluded\n(n=%s)' % h.fmt_number(d['records_screened_excluded'])
    # rnames[6]='Full-text articles assessed\nfor eligibility\n(n=%s)'%h.fmt_number(d['assessed_eligibility'])
    rnames[6] = "Articles' abstracts assessed\nfor eligibility\n(n=%s)" % h.fmt_number(d['assessed_eligibility'])
    rnames[7] = 'Articles excluded,\nwith reasons\n(n=%s)' % h.fmt_number(
        d['assessed_eligibility_excluded'])
    # rnames[7]='Full-text articles excluded,\nwith reasons\n(n=%s)'%d['assessed_eligibility_excluded']
    rnames[8] = 'Studies included in\nqualitative synthesis\n(n=%s)' % h.fmt_number(d['qualitative_synthesis'])
    rnames[9] = 'Studies included in\nquantitative synthesis\nmeta-analysis\n(n=%s)' % h.fmt_number(
        d['quantitative_synthesis'])

    other_rectangles = {
        rnames[1]: mpatch.Rectangle((3, 24), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[2]: mpatch.Rectangle((13, 24), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[3]: mpatch.Rectangle((7, 20), 10, 2, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[4]: mpatch.Rectangle((8, 16), 8, 2, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[5]: mpatch.Rectangle((18, 16), 8, 2, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[6]: mpatch.Rectangle((8, 11), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[7]: mpatch.Rectangle((18, 11), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[8]: mpatch.Rectangle((8, 6), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5),
        rnames[9]: mpatch.Rectangle((8, 1), 8, 3, facecolor='white', edgecolor='black', linewidth=0.5)
    }

    for r_text, r in other_rectangles.items():
        ax.add_artist(r)
        rx, ry = r.get_xy()
        cx = rx + r.get_width() / 2.0
        cy = ry + r.get_height() / 2.0

        ax.annotate(r_text, (cx, cy), color='black',
                    fontsize=4, verticalalignment='center', horizontalalignment='center', rotation=0)

    plt.arrow(x=9, y=24, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=15, y=24, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=12, y=20, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=12, y=16, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=12, y=11, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=12, y=6, dx=0, dy=-1.75, head_width=0.1, linewidth=0.5)
    plt.arrow(x=16, y=17, dx=1.75, dy=0, head_width=0.1, linewidth=0.5)
    plt.arrow(x=16, y=12.5, dx=1.75, dy=0, head_width=0.1, linewidth=0.5)

    ax.set_xlim((-0.5, 27))
    ax.set_ylim((0.5, 28.5))
    ax.set_aspect('equal')

    # # Turn on the minor TICKS, which are required for the minor GRID
    # ax.minorticks_on()

    # # Customize the major grid
    # ax.grid(which='major', linestyle='-', linewidth='0.5', color='red')
    # Customize the minor grid
    # ax.grid(which='minor', linestyle=':', linewidth='0.5', color='black')
    # ax.axis('off')
    fig.frameon = False
    ax.set_axis_off()
    dpi = 300 if plot_type == 'png' else None
    plt.savefig(dest_filename, bbox_inches='tight', dpi=dpi)
    if plot_type != 'pdf':
        plt.savefig(h.remove_extension(dest_filename) + '.pdf', bbox_inches='tight')
