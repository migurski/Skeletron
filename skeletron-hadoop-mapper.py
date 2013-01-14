#!/usr/bin/env python
'''

Test usage:
    cat oakland-sample.json | ./skeletron-hadoop-mapper.py | sort | ./skeletron-hadoop-reducer.py > output.json
'''
from sys import stdin, stdout
from json import load, dumps
from itertools import product

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)08s - %(message)s')

from shapely.geometry import asShape
from Skeletron.output import generalize_geometry
from Skeletron.util import hadoop_feature_line

if __name__ == '__main__':

    geojson = load(stdin)
    pixelwidth = 20
    
    for (feature, zoom) in product(geojson['features'], (12, 13, 14, 15, 16)):

        id = feature.get('id', None)
        prop = feature.get('properties', {})
        geom = asShape(feature['geometry'])
    
        try:
            skeleton = generalize_geometry(geom, pixelwidth, zoom)
            bones = getattr(skeleton, 'geoms', [skeleton])
            prop.update(dict(zoomlevel=zoom, pixelwidth=pixelwidth))
            
            if not skeleton:
                logging.debug('Empty skeleton')
                continue
            
        except Exception, e:
            logging.error(str(e))
            continue
        
        if id is None:
            for (index, bone) in enumerate(bones):
                logging.info('line %d of %d from %s' % (1 + index, len(bones), dumps(prop)))
                print >> stdout, hadoop_feature_line(id, prop, bone)
        else:
            logging.info('%d-part multiline from %s' % (len(bones), dumps(prop)))
            print >> stdout, hadoop_feature_line(id, prop, skeleton)
