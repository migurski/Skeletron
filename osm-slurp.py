from sys import stdin
from math import hypot, ceil
from xml.parsers.expat import ParserCreate

from networkx import Graph
from shapely.geometry import MultiLineString, MultiPolygon, Polygon
from pyproj import Proj

merc = Proj('+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over')

def segmentize(ring, distance):
    """
    """
    coords = [ring.coords[0]]
    
    for curr_coord in list(ring.coords)[1:]:
        prev_coord = coords[-1]
    
        dx, dy = curr_coord[0] - prev_coord[0], curr_coord[1] - prev_coord[1]
        steps = ceil(hypot(dx, dy) / distance)
        count = int(steps)
        
        while count:
            prev_coord = prev_coord[0] + dx/steps, prev_coord[1] + dy/steps
            coords.append(prev_coord)
            count -= 1
    
    return coords

class ParserOSM:

    nodes = None
    ways = None
    way = None

    def __init__(self):
        self.p = ParserCreate()
        self.p.StartElementHandler = self.start_element
        self.p.EndElementHandler = self.end_element
        #self.p.CharacterDataHandler = char_data
    
    def parse(self, input):
        self.nodes = dict()
        self.ways = dict()
        self.p.Parse(input)
        
        parsed = dict()
        
        for (id, way) in self.ways.items():
            if not way['key'][0]:
                # no-name, no way!
                continue
        
            key = tuple(way['key'])
            
            if key not in parsed:
                parsed[key] = []
            
            parsed[key].append(way['nodes'])
        
        line = MultiLineString(parsed[(u'Harrison Street', u'secondary')])
        poly = line.buffer(20, 3)
        
        if hasattr(poly, 'geoms'):
            geoms = []
            
            for geom in poly.geoms:
                exterior = segmentize(poly.exterior, 10)
                interiors = [segmentize(interior, 10) for interior in poly.interiors]
                geoms.append((exterior, interiors))

            poly = MultiPolygon(geoms)
        
        else:
            exterior = segmentize(poly.exterior, 10)
            interiors = [segmentize(interior, 10) for interior in poly.interiors]
            poly = Polygon(exterior, interiors)
            
        print poly
        
        return
        
        print parsed.keys()
        print line.buffer(20, 3)
    
    def start_element(self, name, attrs):
        if name == 'node':
            self.add_node(attrs['id'], float(attrs['lat']), float(attrs['lon']))
        
        elif name == 'way':
            self.add_way(attrs['id'])
        
        elif name == 'tag' and self.way:
            self.tag_way(attrs['k'], attrs['v'])
        
        elif name == 'nd' and attrs['ref'] in self.nodes and self.way:
            self.extend_way(attrs['ref'])
    
    def end_element(self, name):
        if name == 'way':
            self.end_way()

    def add_node(self, id, lat, lon):
        x, y = merc(lon, lat)
        self.nodes[id] = x, y
    
    def add_way(self, id):
        self.way = id
        self.ways[id] = dict(nodes=[], key=[None, None])
    
    def tag_way(self, key, value):
        way = self.ways[self.way]

        if key == 'name':
            way['key'][0] = value
        elif key == 'highway':
            way['key'][1] = value
    
    def extend_way(self, id):
        way, node = self.ways[self.way], self.nodes[id]
        way['nodes'].append(node)
    
    def end_way(self):
        self.way = None

p = ParserOSM()
p.parse(stdin.read())
