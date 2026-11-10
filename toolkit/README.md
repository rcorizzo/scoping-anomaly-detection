# Methodology
## Introduction
This software aims to automate the time-consuming manual steps of the ]PRISMA meta-analysis methodology](https://www.prisma-statement.org/) while identifying and processing the available literature. To perform study collection, scanning, and eligibility evaluation, the toolkit utilizes Natural Language Processing methods to ensure an efficient and exhaustive search of the literature corpus in multiple digital libraries: IEEE, PubMed, MDPI, Elsevier, and Springer. As a result, the toolkit generates detailed list of potentially relevant articles, trend charts over the defined time period of interest, and breakdown on various criteria.

To achieve these goals, the user is required to provide a collection of keywords that are used to identify potentially relevant articles (i.e., phrases that are used to query a digital library) and a set of properties that should be satisfied by the identified articles. The input is further expanded by proposing synonyms to the search properties. Duplicate articles obtained from multiple source libraries or searched keywords are automatically removed. Likewise, for fuzzy matching of search phrases and the actual titles and abstracts, the framework utilizes synonyms and stemming, so that the search is more robust. Additionally, some properties could be denoted as mandatory or option, and the framwork also provides an ability to discard articles based on some exclusion criteria (i.e., it contains some phrases which idnetify articles irrelevant to the study's goals). For more information about the actual implementation, we refer the reader to the study [Automation in Systematic, Scoping and Rapid Reviews by an NLP Toolkit: A Case Study in Enhanced Living Environments](https://link.springer.com/chapter/10.1007/978-3-030-10752-9_1).

More technical details about the duplicate removal process are described in the `Duplicate removal process` subsection. Likewise, in the subsections `apply_stemming` and `apply_phrase_permutations` is described the menchanisms of stemming and permutations of properties and phrases to improve the robustness of the matching. Likewise, the deep learning based approaches for ranking articles per relevancy are described in the `calculate_similarities` subsection below.


## Duplicate removal process
The duplicate removal process relies on the article's link. However, if the same article is indexed in multiple places, for example in Springer and PubMed, then it would contain a different URL. Therefore, we also rely on the article's title (after lowercase conversion and removal of all non-alphanumeric characters).

Note that per the PRISMA methodology, duplicates are removed, and the corresponding generated PRISMA diagram after the "" step shows number related to the articles after the duplicate removal process. Similarly, the `filtered_articles.xlsx` file contains only one version of each article.

### Duplicate handling regarding "Source" / "Digital library"
When searching at multiple sources, the same article could be identified in more than one librarly, for example PubMed (considering that it indexes other libraries as well) and Springer, Elsevier or MDPI. Therefore, in the charts presenting number of articles per source, we count the same article as being identified by all sources (libraries) that contain it. Therefore, it can happen that on the `aggr_source.pdf`, `aggr_source_year_relevant.pdf` and `aggr_keyword_source_relevant.pdf` the total number of articles is greater than on the final block in the PRISMA diagram - `aggr_prisma.pdf`.

For example, the same artcile can be located at [MDPI](https://www.mdpi.com/1424-8220/22/4/1373) and [PubMed](https://pubmed.ncbi.nlm.nih.gov/35214275/). In that case, one of those records will be present in `filtered_articles.xlsx`, but the source diagrams will contain it as identified in both PubMed and MDPI.

### Duplicate handling regarding "Search keywords"
When searching for multiple phrases, such as `"keywords": ["Ambient Assisted Living", "Assisted living", "AAL"]`, the same article could be identified by two or more of the keywords above. Therefore, in the charts presenting number of articles per keyword, we count the same article as being identified by all three keywords. Therefore, it can happen that on the `aggr_keyword_year_relevant.pdf` and 
`aggr_keyword_source_relevant.pdf` the total number of articles is greater than on the final block in the PRISMA diagram - `aggr_prisma.pdf`.


# Description of INPUT data

## Input parameters
The following input parameters need to be configured in the search file:

### keywords
They are the keywords that you would be searching in the digital libraries. Multiple keywords should be comma-separated in different strings. If you have different keywords, then the tool will perform multiple independed searches to the selected libraries and afterwards will remove any duplicate results automatically. So having multiple keywords is actually like having an OR clause in your search.

Example:
```"keywords": ["Ambient Assisted Living", "Assisted living", "AAL"]```
This is like searching ```(Ambient Assisted Living) OR (Assisted living) OR AAL```

### properties
The properties are words or phrases that we search in the: **title, abstract and keywords** section of the article. They are organized in property groups based on semantic similarity and thus facilitate convenient charts.

Example:
```
"properties":[
		{
            "property_group": "Keywords",
            "synonyms": [
                ["object"],
                ["volume"],
                ["image processing", "imaging"],
                ["mobile device", "smart phone", "smart-phone", "cell-phone", "tablet", "smartphone"],
                ["measurement", "estimation", "calculation"],
                ["3D reconstruction"],
                ["contactless measurement", "noncontact measuring", "noncontact measurement"]
            ]
        },
        {
            "property_group": "Volume-estimation Approaches",
            "synonyms": [
                ["multispectral camera"],
                ["projection area"],
                ["height maps"],
                ["Partial least squares"],
                ["LS-SVM", "least squares-support vector machine"],
                ["water displacement"],
                ["active thermography"],
                ["multi-channel neural networks"],
                ["tactile sensors"],
                ["contact sensors", "contact forces"],
                ["power grasp"]
            ],
            "is_mandatory": true
        }]
```

Here, for example, `image processing` and `imaging` are considered synonyms, and whenever one of those word is found in the article, we tag the article with the first synonym (`image processing` in this example).

### is_mandatory
The `"is_mandatory": true` filed in the "Volume-estimation Approaches" group above means that the whole group is mandatory and for teh article to be considered relevant, it has to contain at least one of the properties in this group.

### properties_excluded
This provides a list of excluded properties. So if the article's abstract or title contains at least one of them, it would be considered as **NOT relevant**, even if all other conditions make it relevant.

Example:
```
"properties_excluded": [
		"Review paper", "Review article", "Scoping review", "Systematic review", "Survey paper", "Survey article", "Scoping Survey", "Systematic Survey",
		"Position paper", "Comment article", "Position article", "Communication paper"
	],
```
### properties_mandatory
These are the properties that have to be found in the article, for it to be considered relevant.

Example:
```
"properties_mandatory": [
        ["volume"],
        ["object"],
        ["mobile device", "smart phone", "image", "video", "smartphone", "smart-phone"]
    ],
```

This example is equivalent to the following logical expression:
```"volume" AND "object" AND ("mobile device" OR "smart phone" OR "image" OR "video" OR "smartphone" OR "smart-phone")```

**Important note** The `"is_mandatory": true` extends the list `"properties_mandatory"` so it adds new conditions, making it more restrictive.

**Best practices**: You would define one or multiple property groups that are related to your inclusion criteria and can consider these as mandatory, where as you define additional property groups that contain other properties that you want to tag or label the papers with.

### relevant

This is the number of properties that should be found in the article for it to be considered relevant. By increasing it, the search becomes more restrictive.
Example:
```"relevant": "2"```

### calculate_similarities
This is by default False (if it's missing in the config file), meaning it won't compute a similarity between the search file and the article's abstract and title. The reason is that the deep learning-based similarities are sometimes slow, and their applicability is limited. However, if enabled, there are columns in the generated `filtered_articles.xlsx` file that might help the user in sorting the article based on them. However, their applicability for automatic determining article's relevancy is limited and might eliminate articles that a user might classify as relevant.

Example:
```"calculate_similarities": true```

### libraries
Which libraries are enabled for searching.

Example:
```
"libraries": {
        "ieee": true,
        "pubmed": true,
        "springer": true,
        "elsevier": true,
        "mdpi": true
    }
```

### apply_stemming
The parameter is by default `"apply_stemming": true`, making sure that the abstract, title and searched properties are first stemmed before making a comparison. If you set this to true, the seach will be looking for exact matches, thus making it less robust and indentifying fewer articles. So when searching for `artificial intelligence`, the stemmed alternative is `artifici intellig`, and the search will look for exact matches of this phrase in the stemmed title and abstract.

### apply_phrase_permutations
The parameter is by default `"apply_phrase_permutations": true`, making permutations of multi-word properties. For example, if the property is `artificial intelligence`, this will cause the two permutations: `artificial intelligence` and `intelligence artificial`. Then when trying to find this phrase in the title or abstract, both of the permutations will be searched in the title or abstract.

**Important note:** If also `"apply_stemming": true`, then the permutations would be made based on the stemmed property. So when searching for `artificial intelligence`, it will search for the permutations of its stemmed alternative (`artifici intellig`), therefore trying to find `artifici intellig` or `intellig artifici` in the stemmed title and abstract.

## Exemplary input file
[A full input file with actual data is available here](https://gitlab.com/magix.ai/survey-results/-/blob/master/templates/search_data_example_full.json). It's a good idea to start with this template and modify it per your requirements.

## Property group templates
[This folder](https://gitlab.com/magix.ai/survey-results/-/tree/master/templates) contains JSON templates for some common property groups that can be included in your input file.
A common use case is to remove irrelevant properties from these templates and include them in your `search_data.json` file.
The current templates contain relevant properties for the following property groups. 
- action care focus
- analytics
- beneficiearies
- concerns
- evaluation
- explainability
- feature_selection
- human computer interaction (HCI)
- ML algorithms (XAI - explainable methods)
- ML_algorithms (taxonomy of ML algorithms)
- ML general (general terms)
- ML problem (general ML problems)
- segmentation
- sensors
- study type
- virtual assistants


# Video tutorial of the framework
[The following link](https://drive.google.com/drive/folders/1J1MQ6JTXIyg9LyrOWSi9ryoiS-neF1cU?usp=sharing) contains multiple detailed videos on how to prepare the input parameters and interpret the results.

# Running the code
## Initial run
The basic command for initial running is as follows:
```
python3.8 main.py -f data/GoodBrother_XAI_20211124/search_data.json
```


## Other command-line parameters
Apart from the mandatory parameters to run the framework described above, the user can call the code with the following parameters too:

- `--multithreading=True` - execution of the code with multiple threads.
- `--delete_cache` can be used to delete previously cached results, and download pages again.
- `--start_year=X` - what year the searching should start from
- `--end_year=Y` - what year the searching should run to
- `--repo`
- `--post_process` 
- `--ieee` - whether to crawl ieee or not during execution
- `--pubmed` - whether to crawl pubmed or not during execution
- `--springer` - whether to crawl springer or not during execution
- `--relevant` - the minimum number of relevant properties
- `--add_lin_coef`
- `--capitalize` - whether the properties on the charts should be capitalized
- `--stem` - whether to stem properties and abstracts
- `--graph` - file containing filtered articles to re-plot graphs and charts
- `--plot_type` - what format the charts should be saved in (pdf/png)


## Manual filtering
You can use the `filtered_articles.xlsx` and populate the `Included?` column with `True` or `False` values. Alternatively, you can remove the rows corresponding to irrelevant articles. Then you can send me the file so I can regenerate new charts with only this data.

Then you can regenerate charts with a command like this:
```
python3.8 main.py -f /home/eftim/crawler/article-analysis/data/GoodBrother_XAI_20211124/search_data.json -g /home/eftim/crawler/article-analysis/data/manual_records/filtered_articles_AAL_AI_model_20211215.xlsx
```

## Improving filtering results
Please reach out if you have any questions or ideas for another iteration which may include:
- Increasing the number of minimum relevant (identified) properties
- Providing mandatory properties
- Removing properties with no matches
- Providing new properties or synonyms
- Changing the search keywords
- Providing new properties
- Providing excluded properties

# Description of the OUTPUT
## Output files
The most imortant files that are generated is provided below:

- `search_data_simple.txt` contains a simple description of the search so that it can be embedded into the article.
- `filtered_articles.xlsx` contains the article list – it’s sorted by number of identified properties (descending). Here you should apply the filter *is_article_relevant=TRUE* to see the relevant articles (after num_relevant and mandatory_properties filters are applied). For completeness, this file also shows all the other articles that were considered, but were discarded as irrelevant per the defined inclusion criteria.
- `aggr_source.pdf` - Number of articles per category: considered, invalid years, incomplete data, duplicates, remaining (before applying the num_relevant and mandatory_properties filters), and relevant (after num_relevant and mandatory_properties filters are applied).
- `aggr_year.pdf` - Number of total analyzed articles (after duplicate removal), and number of relevant articles (after num_relevant and mandatory_properties filters are applied).
- `aggr_source_year_relevant.pdf` - number of relevant articles (after num_relevant and mandatory_properties filters are applied) per year and per source. If the same paper is found in multiple sources, it will be attributed to both of them. This is very unlikely because papers from different sources have differnent URLs.d
- `aggr_keyword_source_relevant.pdf` - the number of relevant articles per each keyword and source. If the same paper is found basedon multiple sources, it will be attributed to both of them. This is very unlikely because papers from different sources have differnent URLs.
- `aggr_keyword_year_relevant.pdf` - number of relevant articles (after num_relevant and mandatory_properties filters are applied) per year and per KEYWORD - INCORRECT because we only take the first KEYWORD.
- `aggr_prisma.pdf` - PRISMA methodology flow. Note: there is a newer version of the [chart template available here](https://prisma-statement.org/).
- `aggr_prisma_scoping.pdf` - PRISMA methodology slighltly changed to correspond to scoping reviews.
- `aggr_property_group_year.pdf` - number of relevant articles (after num_relevant and mandatory_properties filters are applied) per property group and year.
- `aggr_property_year_*pdf` - number of relevant articles (after num_relevant and mandatory_properties filters are applied) per property and year. For each property group there is a separate file (you can notice the property group name in the name of the file).
- `filtered_graph_*` - graph about how many articles are there containing a pair of properties
- `heatmap*.pdf` - the heatmap about how many articles are there containing a pair of properties
- `articles.bib` -a bib file with the references, it is convenient if we write a scientific article in latex so we have the references available as well, but be aware, there might be errors in this file so it does not conform to the BibLaTex specification.
- `aggr_property_group_percentage_*pdf` - graph about the number and percentage of articles found per property in a specific property group. For each property group there is a separate file (you can notice the property group name in the name of the file).
- `filtered_graph_data_*_chord_diagram.html` - an interactive chord diagram visualizing the count of relationships between the different properties in a property group present in a single search. For each property group there is a separate file (you can notice the property group name in the name of the file).
- `filtered_graph_data_global_chord_diagram.html` - a chord diagram visualizing the count of relationships between the different property groups present in a single search. Library used for generation of the graph [can be found here](https://holoviews.org/reference/elements/bokeh/Chord.html).
- `filtered_graph_data_sankey_*.html` - a sankey diagram between the different property groups for the lists present in property_group_combinations field in the search_data.json file. For each list in the field, a separate sankey diagram is generated (you can notice the index of the list in the name of the file).
- `filtered_graph_data_sankey_adjacent_property_groups.html` - a sankey diagram containing the relationships between properties of adjacent property groups in the search_data.json file. Library used for generation of the graph [can be found here](https://holoviews.org/reference/elements/bokeh/Sankey.html).
- `heatmap_*pdf` - a heatmap for all the groperty groups.


## filtered_articles.xlsx
Columns present in this detailed resulting file `filtered_articles.xlsx` are provided below:
- `doi` - digital object identifier for each article.
- `link` - link of the article where the information is taken from.
- `title` - title of the article.
- `authors` - authors of the article being analysed.
- `date` - date on which the article was published.
- `year` - the year the article was published.
- `citations` - number of times the article has been cited.
- `abstract` - abstract of the article.
- `keyword` - the keyword for which the search gave the article as a result.
- `source` - the crawler that found this article with using the corresponding keyword.
- `publication` - publication of the article.
- `affiliations` - affiliations of the authors of the article.
- `num_diff_affiliations` - count of the number of different affiliations involved in the article.
- `countries` - countries of the authors of the article.
- `num_diff_countries` - count of the different countries where the authors come from.
- `emails` - emails of the authors of the article.
- `bibtex_id` - id of the bibtex entry in the `articles.bib` file.
- `number_property_groups` - number of different property groups whose properties can be found in the title or abstract of the article.
- `number_properties` - number of different properties found in the title or abstract of the article.
- `all_keywords` - all the keywords whose search has given back the article as a result.
- `all_sources` - all the crawlers that have found the article as a result of a search.
- `is_article_relevant` - is the article relevant per the search criteria, considering the `relevant`, `is_mandatory`, `properties_mandatory`, and `properties_excluded` search parameters.
- `trigram_similarity` - similarity between the title and abstract of the article, and the search_data file calculated using Tf-Idf trigrams.
- `bigram_similarity` - similarity between the title and abstract of the article, and the search_data file calculated using Tf-Idf bigrams.
- `cosine_similarity` - similarity between the title and abstract of the article, and the search_data file calculated using Tf-Idf unigrams. 
- `spacy_similarity` - similarity between title and abstract of the article, and the search_data file calculated using the [spacy](https://spacy.io/usage/linguistic-features) text similarity function from the `en_core_web_sm` corpus.
- `sentence_transformers_similarity` - similarity between title and abstract of the article, and the search_data file calculated using the [BERT model](https://www.sbert.net/docs/usage/semantic_textual_similarity.html) text similarity function from the `sentence-transformers/paraphrase-MiniLM-L6-v2` corpus.




# References
## Exemplary scoping and systematic surveys that utilize the results of this toolkit
Below are also some exemplary articles that were written with the help of this toolkit. You may take a look for inspiration about the structure of the article.

A technical description of the toolkit is described here: [Automation in Systematic, Scoping and Rapid Reviews by an NLP Toolkit: A Case Study in Enhanced Living Environments](https://link.springer.com/chapter/10.1007/978-3-030-10752-9_1)

Connected health survey: [Literature on Wearable Technology for Connected Health: Scoping Review of Research Trends, Advances, and Barriers](https://www.jmir.org/2019/9/e14017/?fbclid=IwAR2c2KL5DDyrVvm5CHwLBGIyZgKbp9pQj47S3fEekVWrlqgEQ_rYWC8F3mo&utm_source=TrendMD&utm_medium=cpc&utm_campaign=JMIR_TrendMD_1)

Metagenomic classification survey: [Literature on Applied Machine Learning in Metagenomic Classification: A Scoping Review](https://www.mdpi.com/2079-7737/9/12/453)

## Citation request
The main idea for this tool originated by [prof. Vladimir Trajkovik](https://scholar.google.com/citations?user=M5LDCMUAAAAJ&hl=en). Its development was lead by Eftim Zdravevski and over the years, multiple students participated in it. If you are using results of this tool, we kindly ask you for a citation of [this paper](https://link.springer.com/chapter/10.1007/978-3-030-10752-9_1) where the original iteration of the tool is described:

Zdravevski, E. et al. (2019). Automation in Systematic, Scoping and Rapid Reviews by an NLP Toolkit: A Case Study in Enhanced Living Environments. In: Ganchev, I., Garcia, N., Dobre, C., Mavromoustakis, C., Goleva, R. (eds) Enhanced Living Environments. Lecture Notes in Computer Science(), vol 11369. Springer, Cham. https://doi.org/10.1007/978-3-030-10752-9_1

BibTex:
```
@Inbook{Zdravevski2019,
author="Zdravevski, Eftim
and Lameski, Petre
and Trajkovik, Vladimir
and Chorbev, Ivan
and Goleva, Rossitza
and Pombo, Nuno
and Garcia, Nuno M.",
editor="Ganchev, Ivan
and Garcia, Nuno M.
and Dobre, Ciprian
and Mavromoustakis, Constandinos X.
and Goleva, Rossitza",
title="Automation in Systematic, Scoping and Rapid Reviews by an NLP Toolkit: A Case Study in Enhanced Living Environments",
bookTitle="Enhanced Living Environments: Algorithms, Architectures, Platforms, and Systems",
year="2019",
publisher="Springer International Publishing",
address="Cham",
pages="1--18",
doi="10.1007/978-3-030-10752-9_1"
}

```


