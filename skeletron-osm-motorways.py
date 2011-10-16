from sys import argv, stdin, stderr, stdout
from itertools import combinations
from optparse import OptionParser
from csv import DictReader
from re import compile
from json import dump
from math import pi

from shapely.geometry import MultiLineString

from Skeletron import waynode_networks, network_multiline, multiline_centerline, mercator
from Skeletron.input import ParserOSM
from Skeletron.util import open_file

earth_radius = 6378137

def highway_key(tags):
    """
    """
    if 'ref' not in tags:
        return None

    if 'highway' not in tags:
        return None
    
    if not tags['ref'] or not tags['highway']:
        return None
    
    return tags['ref'], tags['highway']

optparser = OptionParser(usage="""%prog <osm input file> <geojson output file>""")

defaults = dict(zoom=12, width=10)

optparser.set_defaults(**defaults)

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Zoom level. Default value is %s.' % repr(defaults['zoom']))

optparser.add_option('-w', '--width', dest='width',
                     type='float', help='Line width at zoom level. Default value is %s.' % repr(defaults['width']))

optparser.add_option('-k', '--keys', dest='keys_file',
                     help='Blah blah blah')

if __name__ == '__main__':
    
    options, (input_file, output_file) = optparser.parse_args()
    
    if options.keys_file:

        #
        # The keys file is a CSV with some columns that start with "input"
        # and some columns that start with "output". This script expects
        # there to be an "input ref" and "input highway" and will complain
        # if it isn't found. The output GeoJSON fields are determined by
        # the "output" columns.
        #

        key_rows = list(DictReader(open(options.keys_file)))
        output_columns = [key[7:] for key in key_rows[0].keys() if key.startswith('output ')]
        
        ref_key_keys = [(row['input ref'], row['input highway']) for row in key_rows]
        ref_key_vals = [tuple( [value for (key, value) in row.items() if key.startswith('output ')] ) for row in key_rows]

        ref_keys = zip(ref_key_keys, ref_key_vals)
        ref_keys = dict(ref_keys)

    else:
        ref_keys, output_columns = None, None
    
    buffer = options.width / 2
    buffer *= (2 * pi * earth_radius) / (2**(options.zoom + 8))
    
    #
    # Input
    #
    
    input = open_file(input_file, 'r')
    
    networks = waynode_networks(*ParserOSM().parse(input, highway_key))
    multilines = dict()
    
    for ((refs, highway), network) in networks.items():
        multiline = network_multiline(network)
        
        for ref in refs.split(';'):
            ref = ref.strip()
            ref_key = ref, highway
            
            if ref_keys and ref_key not in ref_keys:
                continue
            
            elif ref_key in ref_keys:
                key = ref_keys[ref_key]
            
            else:
                key = (ref, highway)

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
        
        if output_columns:
            properties = dict(zip(output_columns, key))
        else:
            properties = dict(ref=key[0], highway=key[1])
        
        coords = [[mercator(*point, inverse=True) for point in geom.coords] for geom in centerline.geoms]
        geometry = MultiLineString(coords).__geo_interface__
        
        feature = dict(geometry=geometry, properties=properties)
        geojson['features'].append(feature)
    
    output = open_file(output_file, 'w')
    dump(geojson, output)
