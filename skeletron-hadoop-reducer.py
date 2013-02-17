#!/usr/bin/env python
'''

Test usage:
    cat oakland-sample.json | ./skeletron-hadoop-mapper.py | sort | ./skeletron-hadoop-reducer.py > output.json
'''
from sys import stdout, stdin
from json import loads, JSONEncoder
from re import compile

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)08s - %(message)s')

from Skeletron.util import hadoop_line_features

float_pat = compile(r'^-?\d+\.\d+(e-?\d+)?$')
charfloat_pat = compile(r'^[\[,\,]-?\d+\.\d+(e-?\d+)?$')

if __name__ == '__main__':

    features = []
    
    for line in stdin:
        try:
            features.extend(hadoop_line_features(line))
        
        except Exception, e:
            logging.error(str(e))
            continue

    geojson = dict(type='FeatureCollection', features=features)
    encoder = JSONEncoder(separators=(',', ':'))
    encoded = encoder.iterencode(geojson)
    
    for token in encoded:
        if charfloat_pat.match(token):
            # in python 2.7, we see a character followed by a float literal
            stdout.write(token[0] + '%.5f' % float(token[1:]))
        
        elif float_pat.match(token):
            # in python 2.6, we see a simple float literal
            stdout.write('%.5f' % float(token))
        
        else:
            stdout.write(token)
