from nltk.tokenize import word_tokenize
from help_tools import helpers as h
from nltk.corpus import stopwords
import collections
from help_tools.tools import tools
stop_words = set(stopwords.words('english'))

_country_codes = [
    ("AF", "Afghanistan"),
    ("AL", "Albania"),
    ("DZ", "Algeria"),
    ("AS", "Samoa"),  # American Samoa"
    ("AD", "Andorra"),
    ("AO", "Angola"),
    ("AI", "Anguilla"),
    ("AQ", "Antarctica"),
    ("AG", "Antigua And Barbuda"),
    ("AR", "Argentina"),
    ("AM", "Armenia"),
    ("AW", "Aruba"),
    ("AU", "Australia"),
    ("AT", "Austria"),
    ("AZ", "Azerbaijan"),
    ("BS", "Bahamas"),
    ("BH", "Bahrain"),
    ("BD", "Bangladesh"),
    ("BB", "Barbados"),
    ("BY", "Belarus"),
    ("BE", "Belgium"),
    ("BZ", "Belize"),
    ("BJ", "Benin"),
    ("BM", "Bermuda"),
    ("BT", "Bhutan"),
    ("BO", "Bolivia"),
    ("BA", "Bosnia And Herzegovina"),
    ("BW", "Botswana"),
    ("BV", "Bouvet Island"),
    ("BR", "Brazil"),
    ("IO", "British Indian Ocean Territory"),
    ("BN", "Brunei Darussalam"),
    ("BG", "Bulgaria"),
    ("BF", "Burkina Faso"),
    ("BI", "Burundi"),
    ("KH", "Cambodia"),
    ("CM", "Cameroon"),
    ("CA", "Canada"),
    ("CV", "Cape Verde"),
    ("KY", "Cayman Islands"),
    ("CF", "Central African Republic"),
    ("TD", "Chad"),
    ("CL", "Chile"),
    ("CN", "China"),
    ("CX", "Christmas Island"),
    ("CC", "Cocos Islands"),
    ("CO", "Colombia"),
    ("KM", "Comoros"),
    ("CG", "Congo"),
    ("CD", "Congo"),  # , The Democratic Republic Of The"),
    ("CK", "Cook Islands"),
    ("CR", "Costa Rica"),
    ("CI", "Cote D'ivoire"),
    ("HR", "Croatia"),
    ("CU", "Cuba"),
    ("CY", "Cyprus"),
    ("CZ", "Czech Republic"),
    ("DK", "Denmark"),
    ("DJ", "Djibouti"),
    ("DM", "Dominica"),
    ("DO", "Dominican Republic"),
    ("TP", "East Timor"),
    ("EC", "Ecuador"),
    ("EG", "Egypt"),
    ("SV", "El Salvador"),
    ("GQ", "Guinea"),  # Equatorial
    ("ER", "Eritrea"),
    ("EE", "Estonia"),
    ("ET", "Ethiopia"),
    ("FK", "Falkland Islands"),  # (malvinas)"),
    ("FO", "Faroe Islands"),
    ("FJ", "Fiji"),
    ("FI", "Finland"),
    ("FR", "France"),
    ("GF", "French Guiana"),
    ("PF", "French Polynesia"),
    ("TF", "French Southern Territories"),
    ("GA", "Gabon"),
    ("GM", "Gambia"),
    ("GE", "Georgia"),
    ("DE", "Germany"),
    ("GH", "Ghana"),
    ("GI", "Gibraltar"),
    ("GR", "Greece"),
    ("GL", "Greenland"),
    ("GD", "Grenada"),
    ("GP", "Guadeloupe"),
    # ("GU", "Guam"),
    ("GT", "Guatemala"),
    ("GN", "Guinea"),
    ("GW", "Guinea"),  # -bissau
    ("GY", "Guyana"),
    ("HT", "Haiti"),
    ("HM", "Heard Island And Mcdonald Islands"),
    ("VA", "Vatican"),  # Holy See (vatican City State)"),
    ("HN", "Honduras"),
    ("HK", "Hong Kong"),
    ("HU", "Hungary"),
    ("IS", "Iceland"),
    ("IN", "India"),
    ("ID", "Indonesia"),
    ("IR", "Iran"),  # , Islamic Republic Of"),
    ("IQ", "Iraq"),
    ("IE", "Ireland"),
    ("IL", "Israel"),
    ("IT", "Italy"),
    ("JM", "Jamaica"),
    ("JP", "Japan"),
    ("JO", "Jordan"),
    ("KZ", "Kazakstan"),
    ("KE", "Kenya"),
    ("KI", "Kiribati"),
    ("KP", "North Korea"),  # Democratic People's Republic Of"),
    ("KR", "South Korea"),  # , Republic Of"),
    ("Korea", "South Korea"),  # , Republic Of"),
    ("KV", "Kosovo"),
    ("KW", "Kuwait"),
    ("KG", "Kyrgyzstan"),
    ("LA", "Laos"),  # Lao People's Democratic Republic
    ("LV", "Latvia"),
    ("LB", "Lebanon"),
    ("LS", "Lesotho"),
    ("LR", "Liberia"),
    ("LY", "Libya"),  # Libyan Arab Jamahiriya"),
    ("Libyan", "Libya"),  # Libyan Arab Jamahiriya"),
    ("LI", "Liechtenstein"),
    ("LT", "Lithuania"),
    ("LU", "Luxembourg"),
    ("MO", "Macau"),
    ("MK", "Macedonia"),
    ("MG", "Madagascar"),
    ("MW", "Malawi"),
    ("MY", "Malaysia"),
    ("MV", "Maldives"),
    ("ML", "Mali"),
    ("MT", "Malta"),
    ("MH", "Marshall Islands"),
    ("MQ", "Martinique"),
    ("MR", "Mauritania"),
    ("MU", "Mauritius"),
    ("YT", "Mayotte"),
    ("MX", "Mexico"),
    ("FM", "Micronesia"),
    ("MD", "Moldova"),
    ("MC", "Monaco"),
    ("MN", "Mongolia"),
    ("MS", "Montserrat"),
    ("ME", "Montenegro"),
    ("MA", "Morocco"),
    ("MZ", "Mozambique"),
    ("MM", "Myanmar"),
    ("NA", "Namibia"),
    ("NR", "Nauru"),
    ("NP", "Nepal"),
    # ("NL", "Netherlands"),
    ("NL", "The Netherlands"),
    ("AN", "Antilles"),  # "Netherlands Antilles"
    ("NC", "New Caledonia"),
    ("NZ", "New Zealand"),
    ("NI", "Nicaragua"),
    ("NE", "Niger"),
    ("NG", "Nigeria"),
    ("NU", "Niue"),
    ("NF", "Norfolk Island"),
    ("MP", "Northern Mariana Islands"),
    ("NO", "Norway"),
    ("OM", "Oman"),
    ("PK", "Pakistan"),
    ("PW", "Palau"),
    ("PS", "Palestine"),  # "Palestinian Territory, Occupied"),
    ("Palestina", "Palestine"),  # "Palestinian Territory, Occupied"),
    ("Palestinian", "Palestine"),  # "Palestinian Territory, Occupied"),
    ("PA", "Panama"),
    ("PG", "Guinea"),  # Papua New
    ("PY", "Paraguay"),
    ("PE", "Peru"),
    ("PH", "Philippines"),
    ("PN", "Pitcairn"),
    ("PL", "Poland"),
    ("PT", "Portugal"),
    ("PR", "Puerto Rico"),
    ("QA", "Qatar"),
    ("RE", "Reunion"),
    ("RO", "Romania"),
    ("RU", "Russia"),
    ("Russian Federation", "Russia"),
    ("RW", "Rwanda"),
    ("SH", "Saint Helena"),
    ("KN", "Saint Kitts And Nevis"),
    ("LC", "Saint Lucia"),
    ("PM", "Saint Pierre And Miquelon"),
    ("VC", "Saint Vincent And The Grenadines"),
    ("WS", "Samoa"),
    ("SM", "San Marino"),
    # ("ST", "Sao Tome And Principe"),  # st confuses countries ST -> Saint St.
    ("SA", "Saudi Arabia"),
    ("SN", "Senegal"),
    ("RS", "Serbia"),
    ("SC", "Seychelles"),
    ("SL", "Sierra Leone"),
    ("SG", "Singapore"),
    ("SK", "Slovakia"),
    ("SI", "Slovenia"),
    ("SB", "Solomon Islands"),
    ("SO", "Somalia"),
    ("ZA", "South Africa"),
    # ("GS", "South Georgia And The South Sandwich Islands"),
    ("ES", "Spain"),
    ("LK", "Sri Lanka"),
    ("SD", "Sudan"),
    ("SR", "Suriname"),
    ("SJ", "Svalbard And Jan Mayen"),
    ("SZ", "Swaziland"),
    ("SE", "Sweden"),
    ("CH", "Switzerland"),
    ("SY", "Syrian Arab Republic"),
    ("TW", "Taiwan"),
    ("TJ", "Tajikistan"),
    ("TZ", "Tanzania"),
    ("TH", "Thailand"),
    ("TG", "Togo"),
    ("TK", "Tokelau"),
    ("TO", "Tonga"),
    ("TT", "Trinidad And Tobago"),
    ("TN", "Tunisia"),
    ("TR", "Turkey"),
    ("TM", "Turkmenistan"),
    ("TC", "Turks And Caicos Islands"),
    ("TV", "Tuvalu"),
    ("UG", "Uganda"),
    ("UA", "Ukraine"),
    ("AE", "United Arab Emirates"),
    ("GB", "United Kingdom"),
    ("US", "United States"),
    # ("UM", "United States Minor Outlying Islands"),
    ("UY", "Uruguay"),
    ("UZ", "Uzbekistan"),
    ("VU", "Vanuatu"),
    ("VE", "Venezuela"),
    ("VN", "Viet Nam"),
    ("VG", "Virgin Islands"),  # british
    ("VI", "Virgin Islands"),  # , U.s."),
    ("WF", "Wallis And Futuna"),
    ("EH", "Western Sahara"),
    ("YE", "Yemen"),
    ("ZM", "Zambia"),
    ("ZW", "Zimbabwe"),

    ("USA", "United States"),
    ("Great Britain", "United Kingdom"),
    ("UK", "United Kingdom"),
    ("VN", "Vietnam")
]

_us_states = {'AK': 'Alaska',
              'AL': 'Alabama',
              'AR': 'Arkansas',
              'AZ': 'Arizona',
              'CA': 'California',
              'CO': 'Colorado',
              'CT': 'Connecticut',
              'DC': 'District of Columbia',
              'DE': 'Delaware',
              'FL': 'Florida',
              'GA': 'Georgia',
              'HI': 'Hawaii',
              'IA': 'Iowa',
              'ID': 'Idaho',
              'IL': 'Illinois',
              'IN': 'Indiana',
              'KS': 'Kansas',
              'KY': 'Kentucky',
              'LA': 'Louisiana',
              'MA': 'Massachusetts',
              'MD': 'Maryland',
              'ME': 'Maine',
              'MI': 'Michigan',
              'MN': 'Minnesota',
              'MO': 'Missouri',
              'MS': 'Mississippi',
              'MT': 'Montana',
              'NC': 'North Carolina',
              'ND': 'North Dakota',
              'NE': 'Nebraska',
              'NH': 'New Hampshire',
              'NJ': 'New Jersey',
              'NM': 'New Mexico',
              'NV': 'Nevada',
              'NY': 'New York',
              'OH': 'Ohio',
              'OK': 'Oklahoma',
              'OR': 'Oregon',
              'PA': 'Pennsylvania',
              'RI': 'Rhode Island',
              'SC': 'South Carolina',
              'SD': 'South Dakota',
              'TN': 'Tennessee',
              'TX': 'Texas',
              'UT': 'Utah',
              'VA': 'Virginia',
              'VT': 'Vermont',
              'WA': 'Washington',
              'WI': 'Wisconsin',
              'WV': 'West Virginia',
              'WY': 'Wyoming'}


def simplify_country_name(country):
    words = word_tokenize(h.remove_nonalpha(country.lower(), ' '))
    country_words = tuple([w for w in words if w not in stop_words])
    return country_words


_country_map = dict()
for code, name in _country_codes:
    country_words = simplify_country_name(name)
    _country_map[country_words] = name
    if code not in _us_states:
        _country_map[simplify_country_name(code)] = name

for us_code, name in _us_states.items():
    _country_map[simplify_country_name(name)] = "United States"
    _country_map[simplify_country_name(us_code)] = "United States"

_country_map = collections.OrderedDict(
    sorted(_country_map.items(), key=lambda x: (len(x[0]), len(' '.join(x[0]))), reverse=True))


class Countries(object):
    country_map = _country_map


    @staticmethod
    def process_affiliations(s_affil=None):
        if not s_affil:
            s_affil = ''
        s_affil = s_affil.replace('\t', ';')
        l_affil = [x.strip() for x in s_affil.split(';')]
        affil = ';'.join(l_affil)
        simple_affil = set()  # OrderedDict doesn't support very long keys
        for c_affil in l_affil:
            c_affil = simplify_country_name(c_affil)
            simple_affil.add(c_affil)
        num_affil = len(simple_affil)
        if num_affil == 0:
            affil = 'Unknown'
            num_affil = 1
            countries = 'Unknown'
            num_countries = 1
            return affil, num_affil, countries, num_countries
        countries_l = set()
        for c_affil in simple_affil:
            for country_simplified, country_name in Countries.country_map.items():
                if tools.is_subsequence(country_simplified, c_affil):
                    countries_l.add(country_name)
                    break
            if len(simple_affil) == 0:
                break
        if len(countries_l) > 0:
            countries = ';'.join(countries_l)
            num_countries = len(countries_l)
        else:
            countries = 'Unknown'
            num_countries = 1
        return affil, num_affil, countries, num_countries


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
