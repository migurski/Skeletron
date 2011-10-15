from xml.parsers.expat import ParserCreate

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
        """ Given a file-like stream of OSM XML data, return dictionaries of ways and nodes.
        
            Keys are generated from way tags based on the key_func argument.
        """
        self.nodes = dict()
        self.ways = dict()
        self.key = key_func
        self.p.ParseFile(input)
        return self.ways, self.nodes
    
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
        self.nodes[id] = lat, lon
    
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
