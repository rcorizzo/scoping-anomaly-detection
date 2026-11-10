#!/usr/bin/env bash
cur_fold=`pwd`
for folder in ~/crawler/article-analysis/df_data_sample/* ;
do
    bash ~/crawler/article-analysis/commit_results_specific.sh $folder
done

