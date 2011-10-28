from sys import stderr
from subprocess import Popen, PIPE
from itertools import combinations
    
from shapely.geometry import Point, LineString, Polygon, MultiLineString, MultiPolygon
from pyproj import Proj

try:
    from networkx.algorithms.shortest_paths.astar import astar_path
    from networkx.exception import NetworkXNoPath
    from networkx import Graph
except ImportError:
    # won't work but we can muddle through
    pass

mercator = Proj('+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over')

from .util import simplify_line, densify_line, polygon_rings

def multiline_centerline(multiline, buffer=20, density=10, min_length=40, min_area=100):
    """ Coalesce a linear street network to a centerline.
    
        Accepts and returns instances of shapely LineString and MultiLineString.
    
        Keyword arguments:
        
          buffer
            Size of buffer in map units, should account for ground distance
            between typical carriageways.
          
          density
            Target density of perimeter points in map units, should be
            approximately half the size of buffer.
        
          min_length
            Minimum length of centerline portions to skip spurs and forks,
            should be about twice buffer.
        
          min_area
            Minimum area of roads kinks for them to be maintained through
            generalization by util.simplify_line(), should be approximately
            one quarter of buffer squared.
    """
    if not multiline:
        return False
    
    geoms = hasattr(multiline, 'geoms') and multiline.geoms or [multiline]
    counts = [len(geom.coords) for geom in geoms]

    print >> stderr, ' ', len(geoms), 'linear parts with', sum(counts), 'points',
    
    geoms = [simplify_line(list(geom.coords), min_area) for geom in geoms]
    counts = [len(geom) for geom in geoms]

    print >> stderr, 'reduced to', sum(counts), 'points.'
    
    multiline = MultiLineString(geoms)
    multipoly = multiline_polygon(multiline, buffer)
    
    lines, points = [], 0
    
    for ring in polygon_rings(multipoly):
        polygon = Polygon(ring)
        skeleton = polygon_skeleton(polygon, density)
        routes = skeleton_routes(skeleton, min_length)

        points += sum(map(len, routes))
        lines.extend([simplify_line(route, min_area) for route in routes])
    
    print >> stderr, ' ', points, 'centerline points reduced to', sum(map(len, lines)), 'final points.'
    
    if not lines:
        return False
    
    return MultiLineString(lines)

def graph_routes(graph, find_longest):
    """ Return a list of routes through a network as (x, y) pair lists, with no edge repeated.
    
        Each node in the graph must have a "point" attribute with a Point object.
    """
    # it's destructive
    _graph = graph.copy()
    
    # passed directly to shortest_path()
    weight = find_longest and 'length' or None
    
    # heuristic function for A* path-finding functions, see also:
    # http://networkx.lanl.gov/reference/algorithms.shortest_paths.html#module-networkx.algorithms.shortest_paths.astar
    heuristic = lambda n1, n2: _graph.node[n1]['point'].distance(_graph.node[n2]['point'])
    
    routes = []
    
    while True:
        if not _graph.edges():
            break
    
        leaves = [index for index in _graph.nodes() if _graph.degree(index) == 1]
        
        if len(leaves) == 1 or not find_longest:
            # add Y-junctions because with a single leaf, we'll get nowhere
            leaves += [index for index in _graph.nodes() if _graph.degree(index) == 3]
        
        if len(leaves) == 0:
            # just pick an arbitrary node and its neighbor out of the infinite loop
            node = [index for index in _graph.nodes() if _graph.degree(index) == 2][0]
            neighbor = _graph.neighbors(node)[0]
            leaves = [node, neighbor]

        distances = [(_graph.node[v]['point'].distance(_graph.node[w]['point']), v, w)
                     for (v, w) in combinations(leaves, 2)]
        
        for (distance, v, w) in sorted(distances, reverse=find_longest):
            try:
                indexes = astar_path(_graph, v, w, heuristic, weight)
            except NetworkXNoPath:
                # try another
                continue
    
            for (v, w) in zip(indexes[:-1], indexes[1:]):
                _graph.remove_edge(v, w)
            
            points = [_graph.node[index]['point'] for index in indexes]
            coords = [(point.x, point.y) for point in points]
            routes.append(coords)
            
            # move on to the next possible route
            break
    
    return routes

def waynode_networks(ways, nodes):
    """ Return a dictionary of network graphs from dictionaries of ways and nodes.
        
        Each network graph node will have a "point" attribute with
        the node's location projected to spherical mercator.
    """
    networks = dict()
    
    for way in ways.values():
        key = way['key']
        node_ids = way['nodes']
        
        if key not in networks:
            networks[key] = Graph()
        
        edges = zip(node_ids[:-1], node_ids[1:])
        
        for (id_, _id) in edges:
            point_ = Point(*mercator(*reversed(nodes[id_])))
            _point = Point(*mercator(*reversed(nodes[_id])))
        
            networks[key].add_node(id_, dict(point=point_))
            networks[key].add_node(_id, dict(point=_point))
            networks[key].add_edge(id_, _id)
    
    return networks

def networks_multilines(networks):
    """ Converts dictionary of street line networks to dictionary of multilines.
    """
    multilines = dict()
    
    for (key, network) in networks.items():
        routes = graph_routes(network, False)
        
        if routes:
            print >> stderr, 'Found', key
            multilines[key] = MultiLineString(routes)
        
        else:
            print >> stderr, 'Ignored', key
            continue
        
    return multilines

def multiline_polygon(multiline, buffer=20):
    """ Given a multilinestring, returns a buffered polygon.
    """
    #
    # it seem like it should be possible to just use multiline.buffer(), no?
    # in some cases, for some inputs, this resulted in an incomplete output
    # for unknown reasons, so we'll buffer each part of the line separately
    # and dissolve them together like peasants.
    #
    polys = [line.buffer(buffer, 3) for line in multiline.geoms]
    return reduce(lambda a, b: a.union(b), polys)

def polygon_skeleton(polygon, density=10):
    """ Given a buffer polygon, return a skeleton graph.
    """
    skeleton = Graph()
    points = []
    
    for ring in polygon_rings(polygon):
        points.extend(densify_line(list(ring.coords), density))
    
    if len(points) <= 4:
        # don't bother with this one
        return skeleton
    
    print >> stderr, ' ', len(points), 'perimeter points',
    
    rbox = '\n'.join( ['2', str(len(points))] + ['%.2f %.2f' % (x, y) for (x, y) in points] + [''] )
    
    qvoronoi = Popen('qvoronoi o'.split(), stdin=PIPE, stdout=PIPE)
    output, error = qvoronoi.communicate(rbox)
    voronoi_lines = output.splitlines()
    
    if qvoronoi.returncode:
        raise Exception('Failed with code %s' % qvoronoi.returncode)
    
    vert_count, poly_count = map(int, voronoi_lines[1].split()[:2])
    
    for (index, line) in enumerate(voronoi_lines[2:2+vert_count]):
        point = Point(*map(float, line.split()[:2]))
        if point.within(polygon):
            skeleton.add_node(index, dict(point=point))
    
    for line in voronoi_lines[2+vert_count:2+vert_count+poly_count]:
        indexes = map(int, line.split()[1:])
        for (v, w) in zip(indexes, indexes[1:] + indexes[:1]):
            if v not in skeleton.node or w not in skeleton.node:
                continue
            v1, v2 = skeleton.node[v]['point'], skeleton.node[w]['point']
            line = LineString([(v1.x, v1.y), (v2.x, v2.y)])
            if line.within(polygon):
                skeleton.add_edge(v, w, dict(line=line, length=line.length))
    
    removing = True
    
    while removing:
        removing = False
    
        for index in skeleton.nodes():
            if skeleton.degree(index) == 1:
                depth = skeleton.node[index].get('depth', 0)
                if depth < 20:
                    other = skeleton.neighbors(index)[0]
                    skeleton.node[other]['depth'] = depth + skeleton.edge[index][other]['line'].length
                    skeleton.remove_node(index)
                    removing = True
    
    print >> stderr, 'contain', len(skeleton.edge), 'internal edges.'
    
    return skeleton

def skeleton_routes(skeleton, min_length=25):
    """ Given a skeleton graph, return a series of (x, y) list routes ordered longest to shortest.
    """
    routes = graph_routes(skeleton, True)
    
    return [route for route in routes if LineString(route).length > min_length]
