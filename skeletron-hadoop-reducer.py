#!/usr/bin/env python
'''

Test usage:
    cat oakland-sample.json | ./skeletron-hadoop-mapper.py | sort | ./skeletron-hadoop-reducer.py > output.json
'''
from sys import stdout, stdin
from json import dump, loads

from Skeletron.util import hadoop_line_feature

if __name__ == '__main__':

    features = [hadoop_line_feature(line) for line in stdin]
    geojson = dict(type='FeatureCollection', features=features)
    
    dump(geojson, stdout)
