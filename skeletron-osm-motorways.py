from sys import argv, stdin, stderr, stdout
from optparse import OptionParser
from re import compile
from json import dump
from math import pi

from shapely.geometry import MultiLineString

from Skeletron import network_multiline, multiline_centerline
from Skeletron.input import ParserOSM, mercator

def highway_key(tags):
    """
    """
    if 'ref' not in tags:
        return None

    if 'highway' not in tags:
        return None
    
    if not tags['ref'] or not tags['highway']:
        return None
    
    if tags['highway'] not in ('motorway', 'trunk'):
        return None

    return tags['ref']

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
    buffer *= (2 * pi * 6378137) / (2**(options.zoom + 8))
    
    input = (input_file == '-') and stdin or open(input_file)
    geojson = dict(type='FeatureCollection', features=[])

    network = ParserOSM().parse(input, highway_key)
    multilines = dict()
    
    for (refs, network) in network.items():
        multiline = network_multiline(network)
        
        for ref in refs.split(';'):
            ref = ref.strip()

            if ref in multilines:
                print >> stderr, 'Adding to', ref
                multilines[ref] = multilines[ref].union(multiline)
            
            else:
                print >> stderr, 'Found', ref
                multilines[ref] = multiline
    
    kwargs = dict(buffer=buffer, density=buffer/2, min_length=2*buffer, min_area=(buffer**2)/4)

    print >> stderr, 'Buffer: %(buffer).1f, density: %(density).1f, minimum length: %(min_length).1f, minimum area: %(min_area).1f.' % kwargs
    print >> stderr, '-' * 20

    for (ref, multiline) in multilines.items():
        print >> stderr, ref, str(multiline)[:128]
        
        centerline = multiline_centerline(multiline, **kwargs)
        
        if not centerline:
            continue
        
        coords = [[mercator(*point, inverse=True) for point in geom.coords] for geom in centerline.geoms]
        geometry = MultiLineString(coords).__geo_interface__
        properties = dict(ref=ref)
        
        feature = dict(geometry=geometry, properties=properties)
        geojson['features'].append(feature)
    
    output = (output_file == '-') and stdout or open(output_file, 'w')
    dump(geojson, output)
