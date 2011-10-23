from sys import argv, stdin, stderr, stdout
from itertools import combinations
from optparse import OptionParser
from csv import DictReader
from re import compile
from json import dump
from math import pi

from shapely.geometry import MultiLineString

from Skeletron import waynode_networks, network_multiline, multiline_centerline, mercator
from Skeletron.input import parse_route_relations
from Skeletron.util import open_file

earth_radius = 6378137

optparser = OptionParser(usage="""%prog <osm input file> <geojson output file>""")

defaults = dict(zoom=12, width=10)

optparser.set_defaults(**defaults)

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Zoom level. Default value is %s.' % repr(defaults['zoom']))

optparser.add_option('-w', '--width', dest='width',
                     type='float', help='Line width at zoom level. Default value is %s.' % repr(defaults['width']))

if __name__ == '__main__':
    
    options, (input_file, output_file) = optparser.parse_args()
    
    buffer = options.width / 2
    buffer *= (2 * pi * earth_radius) / (2**(options.zoom + 8))
    
    #
    # Input
    #
    
    input = open_file(input_file, 'r')
    
    networks = waynode_networks(*parse_route_relations(input))
    multilines = dict()
    
    for (key, network) in networks.items():
        multiline = network_multiline(network)
        
        if key in multilines:
            print >> stderr, 'Adding to', key
            multilines[key] = multilines[key].union(multiline)
        
        else:
            print >> stderr, 'Found', key
            multilines[key] = multiline
    
    #
    # Output
    #
    
    kwargs = dict(buffer=buffer, density=buffer/2, min_length=2*buffer, min_area=(buffer**2)/4)
    geojson = dict(type='FeatureCollection', features=[])

    print >> stderr, 'Buffer: %(buffer).1f, density: %(density).1f, minimum length: %(min_length).1f, minimum area: %(min_area).1f.' % kwargs
    print >> stderr, '-' * 20

    for (key, multiline) in sorted(multilines.items()):
        print >> stderr, ', '.join(key), '...'
        
        centerline = multiline_centerline(multiline, **kwargs)
        
        if not centerline:
            continue
        
        properties = dict(network=key[0], ref=key[1], highway=key[2])
        
        coords = [[mercator(*point, inverse=True) for point in geom.coords] for geom in centerline.geoms]
        geometry = MultiLineString(coords).__geo_interface__
        
        feature = dict(geometry=geometry, properties=properties)
        geojson['features'].append(feature)
    
    output = open_file(output_file, 'w')
    dump(geojson, output)
