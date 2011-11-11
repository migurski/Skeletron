from sys import argv, stdin, stderr, stdout
from itertools import combinations
from optparse import OptionParser
from csv import DictReader
from re import compile
from json import dump
from math import pi

from Skeletron import waynode_networks, networks_multilines
from Skeletron.input import parse_route_relation_waynodes
from Skeletron.output import multilines_geojson
from Skeletron.util import open_file

earth_radius = 6378137

optparser = OptionParser(usage="""%prog <osm input file> <geojson output file>""")

defaults = dict(zoom=12, width=15, merge_highways='no')

optparser.set_defaults(**defaults)

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Zoom level. Default value is %s.' % repr(defaults['zoom']))

optparser.add_option('-w', '--width', dest='width',
                     type='float', help='Line width at zoom level. Default value is %s.' % repr(defaults['width']))

optparser.add_option('--merge-highways', dest='merge_highways',
                     choices=('yes', 'no', 'largest'), help='Highway merging behavior: "yes" merges highway tags (e.g. collapses primary and secondary) when they share a network and ref tag, "no" keeps them separate, and "largest" merges but outputs the value of the largest highway (e.g. motorway). Default value is "%s".' % defaults['merge_highways'])

if __name__ == '__main__':
    
    options, (input_file, output_file) = optparser.parse_args()
    
    buffer = options.width / 2
    buffer *= (2 * pi * earth_radius) / (2**(options.zoom + 8))
    
    #
    # Input
    #
    
    input = open_file(input_file, 'r')
    
    ways, nodes = parse_route_relation_waynodes(input, options.merge_highways)
    networks = waynode_networks(ways, nodes)
    multilines = networks_multilines(networks)
    
    #
    # Output
    #
    
    kwargs = dict(buffer=buffer, density=buffer/2, min_length=8*buffer, min_area=(buffer**2)/4)
    
    if options.merge_highways == 'yes':
        def key_properties((network, ref, modifier)):
            return dict(network=network, ref=ref, modifier=modifier)

    else:
        def key_properties((network, ref, modifier, highway)):
            return dict(network=network, ref=ref, modifier=modifier, highway=highway)

    print >> stderr, 'Buffer: %(buffer).1f, density: %(density).1f, minimum length: %(min_length).1f, minimum area: %(min_area).1f.' % kwargs
    print >> stderr, '-' * 20

    geojson = multilines_geojson(multilines, key_properties, **kwargs)
    output = open_file(output_file, 'w')
    dump(geojson, output)
