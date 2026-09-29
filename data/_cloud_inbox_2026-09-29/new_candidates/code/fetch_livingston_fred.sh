#!/bin/sh
# Livingston Survey (Philadelphia Fed) historical files + FRED keyless fredgraph CSVs for never-revised
# Moody's corporate yields. Plain curl, 1.2 s spacing.
W=/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates
cd $W/raw/livingston
B=https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/livingston-survey
for f in historical-data/means.xlsx historical-data/medians.xlsx historical-data/individualdata.xlsx \
         historical-data/MeanGrowthRate.xlsx historical-data/MedianGrowthRate.xlsx \
         historical-data/Alternative_Base_Values.xlsx livingston-release-dates.xlsx \
         livingston-documentation.pdf livingston-data-sources.pdf; do
  curl -s -S -m 180 -o "$(basename $f)" -w "%{http_code} %{size_download} $f\n" "$B/$f"; sleep 1.2
done
cd $W/raw/fred
for s in BAA AAA DBAA DAAA; do
  curl -s -S -m 180 -o "$s.csv" -w "%{http_code} %{size_download} $s\n" "https://fred.stlouisfed.org/graph/fredgraph.csv?id=$s"; sleep 1.2
done
