from copy import deepcopy
from xml.parsers.expat import ParserCreate
from logging import debug

def name_key(tags):
    """ Convert way tags to name keys.
    
        Used by ParserOSM.parse().
    """
    if 'name' not in tags:
        return None
    
    if not tags['name']:
        return None
    
    return (tags['name'], )

def name_highway_key(tags):
    """ Convert way tags to name, highway keys.
    
        Used by ParserOSM.parse().
    """
    if 'name' not in tags:
        return None

    if 'highway' not in tags:
        return None
    
    if not tags['name'] or not tags['highway']:
        return None
    
    return tags['name'], tags['highway']

def network_ref_modifier_key(tags):
    """ Convert relation tags to network, ref keys.
    
        Used by ParserOSM.parse().
    """
    if 'network' not in tags:
        return None

    if 'ref' not in tags:
        return None
    
    if not tags['network'] or not tags['ref']:
        return None
    
    return tags['network'], tags['ref'], tags.get('modifier', '')

def name_highway_ref_key(tags):
    """ Convert way tags to name, highway, ref keys.
    
        Used by ParserOSM.parse().
    """
    if tags.get('highway', None) and tags['highway'].endswith('_link'):
        return tags.get('name', None), tags['highway'][:-5], tags.get('ref', None)
    
    return tags.get('name', None), tags.get('highway', None), tags.get('ref', None)

def parse_street_waynodes(input, use_highway):
    """ Parse OSM XML input, return ways and nodes for waynode_networks().
    
        Uses name_highway_key() for way keys, ignores relations.
    """
    way_key = use_highway and name_highway_key or name_key
    rels, ways, nodes = ParserOSM().parse(input, way_key=way_key)
    
    return ways, nodes

def parse_route_relation_waynodes(input, merge_highways):
    """ Parse OSM XML input, return ways and nodes for waynode_networks().
    
        Uses network_ref_modifier_key() for relation keys, converts way keys to fit.

        Assumes correctly-tagged route relations:
            http://wiki.openstreetmap.org/wiki/Relation:route
    """
    rels, ways, nodes = ParserOSM().parse(input, way_key=name_highway_ref_key, rel_key=network_ref_modifier_key)
    
    #
    # Collapse subrelations to surface ways.
    #
    
    changing = True

    while changing:
        changing = False
    
        for rel in rels.values():
            parts = rel['parts']

            for (index, part) in enumerate(parts):
                if part.startswith('rel:'):
                    rel_id = part[4:]
                
                    if rel_id in rels:
                        # there's a matching subrelation, so pull all
                        # its members up into this one looking for ways.

                        parts[index:index+1] = rels[rel_id]['parts']
                        del rels[rel_id]
                        changing = True
                    else:
                        # no matching relation means drop it on the floor.
                        parts[index:index+1] = []
                        changing = True
            
                elif part.startswith('way:'):
                    # good, we want these
                    pass
            
                else:
                    # not sure what this is, can't be good.
                    parts[index:index+1] = []
                    changing = True
            
            if changing:
                # rels was modified, try another round
                break
    
    #
    # Apply relation keys to ways.
    #
    
    rel_ways = dict()
    
    highways = dict(motorway=9, trunk=8, primary=7, secondary=6, tertiary=5)
    net_refs = dict()
    
    for rel in rels.values():
        for part in rel['parts']:
            # we know from above that they're all "way:".
            way_id = part[4:]
            
            # add the route relation key to the way
            rel_way = deepcopy(ways[way_id])
            way_name, way_hwy, way_ref = rel_way['key']
            rel_net, rel_ref, rel_mod = rel['key']
            
            if merge_highways == 'yes':
                rel_way['key'] = rel_net, rel_ref, rel_mod

            elif merge_highways == 'largest':
                rel_way['key'] = rel_net, rel_ref, rel_mod
                big_hwy = net_refs.get((rel_net, rel_ref), None)
                
                if big_hwy is None or (highways.get(way_hwy, 0) > highways.get(big_hwy, 0)):
                    #
                    # Either we've not yet seen this network/ref combination or
                    # the current highway value is larger than the previously
                    # seen largest one. Make a note of it for later.
                    #
                    net_refs[(rel_net, rel_ref, rel_mod)] = way_hwy

            else:
                rel_way['key'] = rel_net, rel_ref, rel_mod, way_hwy
            
            rel_ways[len(rel_ways)] = rel_way
    
    debug('%d rel_ways, %d nodes' % (len(rel_ways), len(nodes)))
    
    if merge_highways == 'largest':
        #
        # Run through the list again, assigning largest highway
        # values from net_refs dictionary to each way key.
        #
        for (key, rel_way) in rel_ways.items():
            network, ref, modifier = rel_way['key']
            highway = net_refs[(network, ref, modifier)]
            rel_ways[key]['key'] = network, ref, modifier, highway
    
    debug('%d rel_ways, %d nodes' % (len(rel_ways), len(nodes)))
    
    return rel_ways, nodes

class ParserOSM:

    nodes = None
    ways = None
    rels = None
    way = None
    rel = None
    way_key = None
    rel_key = None

    def __init__(self):
        self.p = ParserCreate()
        self.p.StartElementHandler = self.start_element
        self.p.EndElementHandler = self.end_element
        #self.p.CharacterDataHandler = char_data
    
    def parse(self, input, way_key=lambda tags: None, rel_key=lambda tags: None):
        """ Given a file-like stream of OSM XML data, return dictionaries of ways and nodes.
        
            Keys are generated from way tags based on the way_key and ref_key arguments.
        """
        self.nodes = dict()
        self.ways = dict()
        self.rels = dict()
        self.way_key = way_key
        self.rel_key = rel_key
        self.p.ParseFile(input)
        return self.rels, self.ways, self.nodes
    
    def start_element(self, name, attrs):
        if name == 'node':
            self.add_node(attrs['id'], float(attrs['lat']), float(attrs['lon']))
        
        elif name == 'way':
            self.add_way(attrs['id'])
        
        elif name == 'tag' and self.way:
            self.tag_way(attrs['k'], attrs['v'])
        
        elif name == 'nd' and attrs['ref'] in self.nodes and self.way:
            self.extend_way(attrs['ref'])
        
        elif name == 'relation':
            self.add_relation(attrs['id'])
        
        elif name == 'tag' and self.rel:
            self.tag_relation(attrs['k'], attrs['v'])
        
        elif name == 'member':
            if attrs['type'] == 'way' and attrs['ref'] in self.ways and self.rel:
                self.extend_relation(attrs['ref'], 'way')
            
            elif attrs['type'] == 'relation' and self.rel:
                self.extend_relation(attrs['ref'], 'rel')
    
    def end_element(self, name):
        if name == 'way':
            self.end_way()

        elif name == 'relation':
            self.end_relation()

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
        key = self.way_key(way['tags'])
        
        if key:
            way['key'] = key
            del way['tags']

        else:
            del self.ways[self.way]
        
        self.way = None
    
    def add_relation(self, id):
        self.rel = id
        self.rels[id] = dict(parts=[], tags=dict(), key=None)
    
    def tag_relation(self, key, value):
        rel = self.rels[self.rel]
        rel['tags'][key] = value
    
    def extend_relation(self, id, member):
        rel = self.rels[self.rel]
        rel['parts'].append('%(member)s:%(id)s' % locals())
    
    def end_relation(self):
        rel = self.rels[self.rel]
        key = self.rel_key(rel['tags'])
        
        if key:
            rel['key'] = key
            del rel['tags']

        else:
            del self.rels[self.rel]
        
        self.rel = None
