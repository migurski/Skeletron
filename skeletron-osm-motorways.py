from sys import argv, stdin, stderr, stdout
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

if __name__ == '__main__':
    
    options, (input_file, output_file) = optparser.parse_args()
    
    buffer = options.width / 2
    buffer *= (2 * pi * earth_radius) / (2**(options.zoom + 8))
    
    #
    # Input
    #
    
    input = (input_file == '-') and stdin or open(input_file)
    
    network = ParserOSM().parse(input, highway_key)
    multilines = dict()
    
    for (refs, network) in network.items():
        multiline = network_multiline(network)
        
        for ref in refs.split(';'):
            ref = ref.strip()

            if ref in multilines:
                print >> stderr, 'Adding to "%s"' % ref
                multilines[ref] = multilines[ref].union(multiline)
            
            else:
                print >> stderr, 'Found "%s"' % ref
                multilines[ref] = multiline
    
    #
    # Matching
    #
    
    refs = multilines.keys()
    pairs = []
    
    for (this_ref, that_ref) in combinations(refs, 2):
        this_num = numbers_pat.sub(r'\1', this_ref)
        that_num = numbers_pat.sub(r'\1', that_ref)
        
        if this_num == that_num:
            if input is stdin:
                print >> stderr, '"%s" matches "%s"' % (this_ref, that_ref)
                pairs.append((this_ref, that_ref))
    
    for (this_ref, that_ref) in pairs:
        if this_ref not in multilines or not multilines[this_ref]:
            continue
    
        if that_ref not in multilines or not multilines[that_ref]:
            continue
    
        multilines[this_ref] = multilines[this_ref].union(multilines[that_ref])
        del multilines[that_ref]
    
    #
    # Output
    #
    
    kwargs = dict(buffer=buffer, density=buffer/2, min_length=2*buffer, min_area=(buffer**2)/4)
    geojson = dict(type='FeatureCollection', features=[])

    print >> stderr, 'Buffer: %(buffer).1f, density: %(density).1f, minimum length: %(min_length).1f, minimum area: %(min_area).1f.' % kwargs
    print >> stderr, '-' * 20

    for (ref, multiline) in multilines.items():
        print >> stderr, ref, '...'
        
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
