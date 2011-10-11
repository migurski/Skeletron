from sys import argv, stdin, stderr
from optparse import OptionParser
from json import dump

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

defaults = dict()

optparser.set_defaults(**defaults)

if __name__ == '__main__':
    
    options, (input_file, output_file) = optparser.parse_args()
    
    input = (input_file == '-') and stdin or open(input_file)
    output = dict(type='FeatureCollection', features=[])

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
    
    for (ref, multiline) in multilines.items():
        print ref, str(multiline)[:128]
        
        centerline = multiline_centerline(multiline, buffer=400, density=100, min_length=400)
        
        if not centerline:
            continue
        
        coords = [[mercator(*point, inverse=True) for point in geom.coords] for geom in centerline.geoms]
        geometry = MultiLineString(coords).__geo_interface__
        properties = dict(ref=ref)
        
        feature = dict(geometry=geometry, properties=properties)
        output['features'].append(feature)

dump(output, open(output_file, 'w'))
