from sys import stderr
from subprocess import Popen, PIPE
from itertools import combinations
    
from shapely.geometry import Point, LineString, Polygon, MultiLineString, MultiPolygon
from networkx.algorithms.shortest_paths.generic import shortest_path, shortest_path_length
from networkx.exception import NetworkXNoPath
from networkx import Graph

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
    polygon = multiline_polygon(multiline, buffer)
    skeleton = polygon_skeleton(polygon, density)
    routes = skeleton_routes(skeleton, min_length)
    lines = [simplify_line(route, min_area) for route in routes]
    
    print >> stderr, ' ', sum(map(len, routes)), 'centerline points reduced to', sum(map(len, lines)), 'final points.'
    
    if not lines:
        return False
    
    return MultiLineString(lines)

def graph_routes(graph, weight):
    """ Return a list of routes through a network as (x, y) pair lists, with no edge repeated.
    
        Each node in the graph must have a "point" attribute with a Point object.
        
        Weight is passed directly to shortest_path() and shortest_path_length()
        in networkx.algorithms.shortest_paths.generic.
    """
    # it's destructive
    _graph = graph.copy()
    
    routes = []
    
    while True:
        leaves = [index for index in _graph.nodes() if _graph.degree(index) == 1]
        
        paths = []
        
        for (v, w) in combinations(leaves, 2):
            try:
                path = shortest_path_length(_graph, v, w, weight), v, w
            except NetworkXNoPath:
                pass
            else:
                paths.append(path)
    
        if not paths:
            break
        
        paths.sort(reverse=True)
        indexes = shortest_path(_graph, paths[0][1], paths[0][2], weight)

        for (v, w) in zip(indexes[:-1], indexes[1:]):
            _graph.remove_edge(v, w)
        
        points = [_graph.node[index]['point'] for index in indexes]
        coords = [(point.x, point.y) for point in points]
        routes.append(coords)

        if not _graph.edges():
            break
    
    return routes

def network_multiline(network):
    """ Given a street network graph, returns a multilinestring.
    """
    routes = graph_routes(network, None)
    
    return routes and MultiLineString(routes) or None

def multiline_polygon(multiline, buffer=20):
    """ Given a multilinestring, returns a buffered polygon.
    """
    return multiline.buffer(buffer, 3)

def polygon_skeleton(polygon, density=10):
    """ Given a buffer polygon, return a skeleton graph.
    """
    points = []
    
    for ring in polygon_rings(polygon):
        points.extend(densify_line(list(ring.coords), density))
    
    print >> stderr, ' ', len(points), 'perimeter points',
    
    rbox = '\n'.join( ['2', str(len(points))] + ['%.2f %.2f' % (x, y) for (x, y) in points] + [''] )
    
    qvoronoi = Popen('qvoronoi o'.split(), stdin=PIPE, stdout=PIPE)
    output, error = qvoronoi.communicate(rbox)
    voronoi_lines = output.splitlines()
    
    skeleton = Graph()
    
    if qvoronoi.returncode:
        print 'Failed with code', qvoronoi.returncode
        return skeleton
    
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
    routes = graph_routes(skeleton, 'length')
    
    return [route for route in routes if LineString(route).length > min_length]
