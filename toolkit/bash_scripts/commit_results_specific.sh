#!/usr/bin/env bash
folder=$1
cur_fold=`pwd`
article_analysis_folder=/mnt/sda/article-analysis
if [ -z "$folder" ]
then
      folder=$article_analysis_folder
fi
survey_results_folder=/home/eftim/crawler/survey-results/results/
cd $article_analysis_folder
results_name=`basename $folder`
echo Processing: $folder/results*
cp $folder/search_data.json $folder/results/search_data_original.json
for results_folder in $folder/results* ;
do
    if [[ -d $results_folder ]]; then
        echo Processing folder: $results_folder
        archive=`basename $results_folder`_${results_name}.zip
        echo Archive with results: $archive
        if [[ ! -f $archive ]]; then
            echo Archiving to $archive
            cd $results_folder
            for image_file in `ls *pdf` ; do
                image_file_out=${image_file}_cr.pdf
                pdfcrop --margins 5 $image_file $image_file_out
                mv $image_file_out $image_file
            done
            for image_file in `ls *pdf` ; do echo $image_file; done
#            zip $archive aggr*pdf aggr*png *prisma* aggr*csv aggr*xlsx *bib *txt *json plot* filtered_articles.xlsx filtered_graph*spring* filtered_graph*gml filtered_graph_data.csv articles_stemmed.csv
#            zip $archive aggr*pdf aggr*png *prisma* aggr*xlsx *bib search* status* filtered_articles*xlsx filtered_graph*pdf articles_invalid.xlsx heatmap* filtered_articles_graphs/* filtered_articles_graphs/properties_graphs/*
             zip $archive emails.txt *pdf *png *xlsx *html *bib search* status* filtered_articles_graphs/* filtered_articles_graphs/properties_graphs/*
        fi
        ls -lah $archive
        echo Moving: mv $archive $survey_results_folder
        mv $archive $survey_results_folder
        cd $survey_results_folder
        git add -f $archive
        echo Current result files
        ls -lah *
        echo "Pushing results to survey-results repo for $archive"
        git commit -m "$archive"
    fi
done
cd $survey_results_folder && git push origin

cd $cur_fold
