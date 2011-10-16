from optparse import OptionParser
from itertools import product
from csv import writer

from Skeletron.input import ParserOSM
from Skeletron.util import open_file

optparser = OptionParser(usage="""%prog [options] <osm input file> <csv output file>

Extract unique tag value combinations from OpenStreetMap XML input, useful when
preparing keys file for use by skeletron-osm-motorways.py.""")

defaults = dict(tags='ref,highway')

optparser.set_defaults(**defaults)

optparser.add_option('-t', '--tags', dest='tags',
                     help='Comma-delimited list of tags. Default value is %s.' % repr(defaults['tags']))

if __name__ == '__main__':
    
    options, (input_file, output_file) = optparser.parse_args()
    
    input = open_file(input_file, 'r')
    output = writer(open_file(output_file, 'w'))
    
    tag_names = options.tags.split(',')
    output.writerow(['input ' + tag for tag in tag_names])
    
    def key_func(way_tags):
        return tuple( [way_tags.get(tag_name, None) for tag_name in tag_names] )

    ways, nodes = ParserOSM().parse(input, key_func)
    
    rows = set()
    
    for way in ways.values():
        key = way['key']
        
        # break tag values up along semicolons
        row = [cell and cell.split(';') or [None] for cell in key]
        
        # put all the unique combinations in a set
        for key in product(*row):
            rows.add(tuple(key))
    
    for row in sorted(rows):
        output.writerow([value and value.encode('utf8') for value in row])
