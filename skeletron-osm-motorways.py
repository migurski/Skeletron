from sys import argv, stdin, stderr, stdout
from csv import DictReader
from itertools import combinations
from optparse import OptionParser
from re import compile
from json import dump
from math import pi

from shapely.geometry import MultiLineString

from Skeletron import network_multiline, multiline_centerline
from Skeletron.input import ParserOSM, mercator

numbers_pat = compile(r'^.*?(\d+)(\D.*)?$')
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
    
    #if tags['highway'] not in ('motorway', 'trunk'):
    #    return None

    return tags['ref']

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
        ref_keys = [(row['ref'], (row['network'], row['number'])) for row in DictReader(open(options.keys_file))]
        ref_keys = dict(ref_keys)

    else:
        ref_keys = None
    
    buffer = options.width / 2
    buffer *= (2 * pi * earth_radius) / (2**(options.zoom + 8))
    
    #
    # Input
    #
    
    input = (input_file == '-') and stdin or open(input_file)
    
    networks = ParserOSM().parse(input, highway_key)
    multilines = dict()
    
    for (refs, network) in networks.items():
        multiline = network_multiline(network)
        
        for ref in refs.split(';'):
            ref = ref.strip()
            
            if ref_keys and ref not in ref_keys:
                continue
            
            elif ref in ref_keys:
                key = None, ref_keys[ref][0], ref_keys[ref][1]
            
            else:
                key = ref, None, None

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

    for ((ref, network, number), multiline) in sorted(multilines.items()):
        print >> stderr, ref, network, number, '...'
        
        centerline = multiline_centerline(multiline, **kwargs)
        
        if not centerline:
            continue
        
        properties = dict(ref=ref, network=network, number=number)
        coords = [[mercator(*point, inverse=True) for point in geom.coords] for geom in centerline.geoms]
        geometry = MultiLineString(coords).__geo_interface__
        
        feature = dict(geometry=geometry, properties=properties)
        geojson['features'].append(feature)
    
    output = (output_file == '-') and stdout or open(output_file, 'w')
    dump(geojson, output)
