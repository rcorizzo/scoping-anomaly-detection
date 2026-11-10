#!/usr/bin/env bash
dpi=$1
if [ -z "dpi" ]
then
      dpi=300
fi
#convert -density 150 -trim /Users/eftim/Repositories/scd-framework/Elektro-Ljubljana/documents/table_lineage/lineage_1_data_mart.d_koncentrator.pdf /Users/eftim/Repositories/scd-framework/Elektro-Ljubljana/documents/table_lineage/lineage_1_data_mart.d_koncentrator%d.png
#
#
#gs -dNOPAUSE -sDEVICE=jpeg -r200 -dJPEGQ=100 -sOutputFile=/Users/eftim/Repositories/scd-framework/Elektro-Ljubljana/documents/table_lineage/lineage_1_data_mart.d_koncentrator-%02d.jpg /Users/eftim/Repositories/scd-framework/Elektro-Ljubljana/documents/table_lineage/lineage_1_data_mart.d_koncentrator.pdf -dBATCH


for i in *.pdf
do 
  convert -density 300 -trim "$i" "$i".png
done
