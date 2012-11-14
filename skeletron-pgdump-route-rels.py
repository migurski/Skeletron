from sys import stdout, stderr
from bz2 import BZ2File
from xml.etree.ElementTree import Element, ElementTree
from itertools import count
from multiprocessing import JoinableQueue, Process

from psycopg2 import connect
from shapely.geometry import LineString

def write_groups(queue):
    '''
    '''
    names = ('routes-%06d.osm.bz2' % id for id in count(1))
    
    while True:
        try:
            group = queue.get(timeout=5)
        except:
            print 'bah'
            break
        
        tree = make_group_tree(group)
        file = BZ2File(names.next(), mode='w')

        tree.write(file)
        file.close()

def get_relations_list(db):
    '''
    '''
    db.execute('''SELECT id, tags
                  FROM planet_osm_rels
                  WHERE 'network' = ANY(tags)
                    AND 'ref' = ANY(tags)
                  ''')
    
    relations = []
    
    for (id, tags) in db.fetchall():
        tags = dict([keyval for keyval in zip(tags[0::2], tags[1::2])])
        
        # Skip bike crap
        if tags.get('network', '') in ('lcn', 'rcn', 'ncn', 'icn', 'mtb'):
            continue
        
        # Skip walking crap
        if tags.get('network', '') in ('lwn', 'rwn', 'nwn', 'iwn'):
            continue

        # Skip rail crap
        if tags.get('route', '') in ('bus', 'tram', 'train', 'subway'):
            continue
        
        # Just the 80's for now.
        if tags.get('network', '') not in ('US:I', ): continue
        if not tags.get('ref', '').endswith('80'): continue
        if len(tags.get('ref', '')) < 3: continue
        
        relations.append((id, tags))
    
    return relations

def get_relation_ways(db, rel_id):
    '''
    '''
    rel_ids = [rel_id]
    rels_seen = set()
    way_ids = set()
    
    while rel_ids:
        rel_id = rel_ids.pop(0)
        
        if rel_id in rels_seen:
            break
        
        rels_seen.add(rel_id)
        
        db.execute('''SELECT members
                      FROM planet_osm_rels
                      WHERE id = %d''' \
                    % rel_id)
        
        try:
            (members, ) = db.fetchone()

        except TypeError:
            # missing relation
            continue
        
        if not members:
            continue
        
        for member in members[0::2]:
            if member.startswith('r'):
                rel_ids.append(int(member[1:]))
            
            elif member.startswith('w'):
                way_ids.add(int(member[1:]))
    
    return way_ids

def get_way_tags(db, way_id):
    '''
    '''
    db.execute('''SELECT tags
                  FROM planet_osm_ways
                  WHERE id = %d''' \
                % way_id)
    
    try:
        (tags, ) = db.fetchone()
    except TypeError:
        # missing way
        return dict()
    
    tags = dict([keyval for keyval in zip(tags[0::2], tags[1::2])])
    
    return tags

def get_way_linestring(db, way_id):
    '''
    '''
    db.execute('''SELECT (n.lon * 0.0000001)::float AS lon,
                         (n.lat * 0.0000001)::float AS lat
                  FROM (
                    SELECT unnest(nodes)::int AS id
                    FROM planet_osm_ways
                    WHERE id = %d
                  ) AS w,
                  planet_osm_nodes AS n
                  WHERE n.id = w.id''' \
                % way_id)
    
    coords = db.fetchall()
    
    if len(coords) < 2:
        return None
    
    return LineString(coords)

def cascaded_union(shapes):
    '''
    '''
    if len(shapes) == 0:
        return None
    
    if len(shapes) == 1:
        return shapes[0]
    
    if len(shapes) == 2:
        if shapes[0] and shapes[1]:
            return shapes[0].union(shapes[1])
        
        if shapes[0] is None:
            return shapes[1]
        
        if shapes[1] is None:
            return shapes[0]
        
        return None
    
    cut = len(shapes) / 2
    
    shapes1 = cascaded_union(shapes[:cut])
    shapes2 = cascaded_union(shapes[cut:])
    
    return cascaded_union([shapes1, shapes2])

def relation_key(tags):
    '''
    '''
    return (tags.get('network', ''), tags.get('ref', ''), tags.get('modifier', ''))

def gen_relation_groups(relations):
    '''
    '''
    relation_keys = [relation_key(tags) for (id, tags) in relations]
    
    group, coords, last_key = [], 0, None
    
    for (key, (id, tags)) in sorted(zip(relation_keys, relations)):

        if coords > 100000 and key != last_key:
            yield group
            group, coords = [], 0
        
        way_ids = get_relation_ways(db, id)
        way_tags = [get_way_tags(db, way_id) for way_id in way_ids]
        way_lines = [get_way_linestring(db, way_id) for way_id in way_ids]
        rel_coords = sum([len(line.coords) for line in way_lines if line])
        #multiline = cascaded_union(way_lines)
        
        if rel_coords > 1000:
            from operator import add
            points = reduce(add, [list(line.coords) for line in way_lines if line])
            
            import numpy, math
            
            # cribbed from http://stackoverflow.com/questions/7059841/estimating-aspect-ratio-of-a-convex-hull
            xy = numpy.vstack(points).T
            eigvals, eigvecs = numpy.linalg.eig(numpy.cov(xy))
            
            print xy.shape, eigvals,
            print sorted([(val, 180 * math.atan2(y, x) / math.pi) for (val, (x, y)) in zip(eigvals, eigvecs.T)], reverse=True)[0][1], 'degrees'
        
        print >> stderr, ', '.join(key), '--', rel_coords, 'nodes'
        
        group.append((id, tags, way_tags, way_lines))
        coords += rel_coords
        last_key = key

    yield group

def make_group_tree(group):
    '''
    '''
    ids = (str(-id) for id in count(1))
    osm = Element('osm', dict(version='0.6'))

    for (id, tags, way_tags, way_lines) in group:
    
        rel = Element('relation', dict(id=ids.next(), version='1', timestamp='0000-00-00T00:00:00Z'))
        
        for (k, v) in tags.items():
            rel.append(Element('tag', dict(k=k, v=v)))
        
        for (tags, line) in zip(way_tags, way_lines):
            if not line:
                continue
        
            way = Element('way', dict(id=ids.next(), version='1', timestamp='0000-00-00T00:00:00Z'))
            
            for (k, v) in tags.items():
                way.append(Element('tag', dict(k=k, v=v)))
            
            for coord in line.coords:
                lon, lat = '%.7f' % coord[0], '%.7f' % coord[1]
                node = Element('node', dict(id=ids.next(), lat=lat, lon=lon, version='1', timestamp='0000-00-00T00:00:00Z'))
                nd = Element('nd', dict(ref=node.attrib['id']))

                osm.append(node)
                way.append(nd)
            
            rel.append(Element('member', dict(type='way', ref=way.attrib['id'])))
            
            osm.append(way)
        
        osm.append(rel)
    
    return ElementTree(osm)

if __name__ == '__main__':

    queue = JoinableQueue()
    
    group_writer = Process(target=write_groups, args=(queue, ))
    group_writer.start()
    
    db = connect(host='localhost', user='gis', database='gis', password='gis').cursor()
    
    relations = get_relations_list(db)
    
    for group in gen_relation_groups(relations):
        queue.put(group)

        print >> stderr, '-->', len(group), 'relations'
        print >> stderr, '-' * 80
    
    group_writer.join()
