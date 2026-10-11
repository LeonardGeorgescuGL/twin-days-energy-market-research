#!/usr/bin/env bash
# Pasul 1b: descarcare și dezarhivare prețurile orare de la Ember (licență CC-BY 4.0)
set -e

mkdir -p data
wget -c -P data https://files.ember-energy.org/public-downloads/price/outputs/european_wholesale_electricity_price_data_hourly.zip
unzip -o data/european_wholesale_electricity_price_data_hourly.zip -d data/hourly

echo
echo "Gata. Fișierele dezarhivate:"
ls -lh data/hourly
