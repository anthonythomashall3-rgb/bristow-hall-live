#!/bin/sh
# Fetch Survey of Professional Forecasters files (Philadelphia Fed). Plain curl UA, 1.2 s spacing.
W=/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates
D=$W/raw/spf; mkdir -p $D; cd $D
B=https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/survey-of-professional-forecasters
for f in historical-data/meanLevel.xlsx historical-data/meanGrowth.xlsx historical-data/medianLevel.xlsx \
         historical-data/medianGrowth.xlsx historical-data/prob.xlsx historical-data/SPFmicrodata.xlsx \
         historical-data/Dispersion_1.xlsx anxious-index/anxious_index_chart.xlsx \
         spf-release-dates.txt spf-documentation.pdf spf-caveats.pdf spf-data-sources.pdf \
         annual-historical-values-by-survey-date-selected-variables.xlsx; do
  o=$(basename $f)
  curl -s -S -m 180 -o "$o" -w "%{http_code} %{size_download} $o\n" "$B/$f"
  sleep 1.2
done
