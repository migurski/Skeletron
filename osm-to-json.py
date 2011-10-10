from sys import stdin, argv
from math import hypot, ceil
from json import dump

from shapely.geometry import Polygon, MultiLineString

from Skeletron import network_multiline, multiline_polygon, polygon_skeleton, skeleton_routes
from Skeletron.input import ParserOSM, merc

p = ParserOSM()
g = p.parse(stdin.read())

output = dict(type='FeatureCollection', features=[])

for key in g:
    print key
    network = g[key]
    
    if not network.edges():
        continue
    
    lines = network_multiline(network)
    poly = multiline_polygon(lines)
    skeleton = polygon_skeleton(poly)
    routes = skeleton_routes(skeleton)
    
    if not routes:
        continue
    
    coords = [[merc(*point, inverse=True) for point in route] for route in routes]
    geometry = MultiLineString(coords).__geo_interface__
    properties = dict(name=key[0], highway=key[1])
    
    feature = dict(geometry=geometry, properties=properties)
    output['features'].append(feature)

dump(output, open(argv[2], 'w'))
