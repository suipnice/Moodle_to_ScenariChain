#!/bin/bash
# -*- coding: utf-8 -*-

rm -R results
python convert_XML.py

# cp templates/Opale36/.wsp* results/
rm results.scar
zip -r results.scar results/* >/dev/null

echo Vos exercices sont prets à etre importés dans l’archive "results.scar"