from json import load, dump
from optparse import OptionParser
import logging

from Skeletron.output import generalize_geojson_feature

earth_radius = 6378137

optparser = OptionParser(usage="""%prog [options] <geojson input file> <geojson output file>

Accepts GeoJSON input and generates GeoJSON output.""")

defaults = dict(zoom=12, width=15, loglevel=logging.INFO)

optparser.set_defaults(**defaults)

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Zoom level. Default value is %s.' % repr(defaults['zoom']))

optparser.add_option('-w', '--width', dest='width',
                     type='float', help='Line width at zoom level. Default value is %s.' % repr(defaults['width']))

optparser.add_option('-v', '--verbose', dest='loglevel',
                     action='store_const', const=logging.DEBUG,
                     help='Output extra progress information.')

optparser.add_option('-q', '--quiet', dest='loglevel',
                     action='store_const', const=logging.WARNING,
                     help='Output no progress information.')

if __name__ == '__main__':

    options, (input_file, output_file) = optparser.parse_args()

    logging.basicConfig(level=options.loglevel, format='%(levelname)08s - %(message)s')
    
    #
    # Input
    #
    
    input = load(open(input_file, 'r'))
    features = [generalize_geojson_feature(feature, options.width, options.zoom) for feature in input['features']]
    
    #
    # Output
    #
    
    output = dict(type='FeatureCollection', features=filter(None, features))
    dump(output, open(output_file, 'w'))
