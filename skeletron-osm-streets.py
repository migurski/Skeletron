#!/usr/bin/env python
""" Run with "--help" flag for more information.

Accepts OpenStreetMap XML input and generates GeoJSON output for streets
using the "name" and "highway" tags to group collections of ways.
"""

from sys import argv, stdin, stderr, stdout
from itertools import combinations
from optparse import OptionParser
from csv import DictReader
from re import compile
from json import dump
from math import pi

from StreetNames import short_street_name

from Skeletron import waynode_multilines
from Skeletron.input import parse_street_waynodes
from Skeletron.output import multilines_geojson
from Skeletron.util import open_file

earth_radius = 6378137

optparser = OptionParser(usage="""%prog [options] <osm input file> <geojson output file>

Accepts OpenStreetMap XML input and generates GeoJSON output for streets
using the "name" and "highway" tags to group collections of ways.""")

defaults = dict(zoom=12, width=10, use_highway=True)

optparser.set_defaults(**defaults)

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Zoom level. Default value is %s.' % repr(defaults['zoom']))

optparser.add_option('-w', '--width', dest='width',
                     type='float', help='Line width at zoom level. Default value is %s.' % repr(defaults['width']))

optparser.add_option('--ignore-highway', dest='use_highway',
                     action='store_false', help='Ignore differences between highway tags (e.g. collapse primary and secondary) when they share a name.')

if __name__ == '__main__':
    
    options, (input_file, output_file) = optparser.parse_args()
    
    buffer = options.width / 2
    buffer *= (2 * pi * earth_radius) / (2**(options.zoom + 8))
    
    #
    # Input
    #
    
    input = open_file(input_file, 'r')
    
    ways, nodes = parse_street_waynodes(input, options.use_highway)
    multilines = waynode_multilines(ways, nodes)
    
    #
    # Output
    #
    
    kwargs = dict(buffer=buffer, density=buffer/2, min_length=2*buffer, min_area=(buffer**2)/4)
    
    if options.use_highway:
        def key_properties((name, highway)):
            return dict(name=name, highway=highway,
                        zoomlevel=options.zoom, pixelwidth=options.width,
                        shortname=short_street_name(name))
    else:
        def key_properties((name, )):
            return dict(name=name,
                        zoomlevel=options.zoom, pixelwidth=options.width,
                        shortname=short_street_name(name))

    print >> stderr, 'Buffer: %(buffer).1f, density: %(density).1f, minimum length: %(min_length).1f, minimum area: %(min_area).1f.' % kwargs
    print >> stderr, '-' * 20

    geojson = multilines_geojson(multilines, key_properties, **kwargs)
    output = open_file(output_file, 'w')
    dump(geojson, output)
