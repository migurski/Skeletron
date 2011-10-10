from xml.parsers.expat import ParserCreate

from shapely.geometry import Point
from pyproj import Proj
from networkx import Graph

merc = Proj('+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over')

def name_highway_key(tags):
    """
    """
    if 'name' not in tags:
        return None

    if 'highway' not in tags:
        return None
    
    if not tags['name'] or not tags['highway']:
        return None
    
    if tags['highway'] == 'motorway':
        return None

    return (tags['name'], tags['highway'])

class ParserOSM:

    nodes = None
    ways = None
    way = None
    key = None

    def __init__(self):
        self.p = ParserCreate()
        self.p.StartElementHandler = self.start_element
        self.p.EndElementHandler = self.end_element
        #self.p.CharacterDataHandler = char_data
    
    def parse(self, input, key_func=name_highway_key):
        self.nodes = dict()
        self.ways = dict()
        self.key = key_func
        self.p.Parse(input)
        return self.graph_response()
    
    def graph_response(self):
        graphs = dict()
        
        for (id, way) in self.ways.items():
            key = way['key']
            node_ids = way['nodes']
            
            if key not in graphs:
                graphs[key] = Graph()
            
            edges = zip(node_ids[:-1], node_ids[1:])
            
            for (id_, _id) in edges:
                graphs[key].add_node(id_, dict(point=self.nodes[id_]))
                graphs[key].add_node(_id, dict(point=self.nodes[_id]))
                graphs[key].add_edge(id_, _id)
        
        return graphs
    
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
        self.nodes[id] = Point(x, y)
    
    def add_way(self, id):
        self.way = id
        self.ways[id] = dict(nodes=[], tags=dict(), key=None)
    
    def tag_way(self, key, value):
        way = self.ways[self.way]
        way['tags'][key] = value
    
    def extend_way(self, id):
        way = self.ways[self.way]
        way['nodes'].append(id)
    
    def end_way(self):
        way = self.ways[self.way]
        key = self.key(way['tags'])
        
        if key:
            way['key'] = key
            del way['tags']

        else:
            del self.ways[self.way]
        
        self.way = None
