from subprocess import Popen, PIPE
from itertools import combinations
    
from shapely.geometry import Point, LineString, Polygon, MultiLineString, MultiPolygon
from networkx.algorithms.shortest_paths.generic import shortest_path, shortest_path_length
from networkx.exception import NetworkXNoPath
from networkx import Graph

from .util import densify_line

def network_multiline(network):
    """ Given a street network graph, returns a multilinestring.
    """
    pairs = [(network.node[a]['point'], network.node[b]['point']) for (a, b) in network.edges()]
    lines = [((p1.x, p1.y), (p2.x, p2.y)) for (p1, p2) in pairs]
    multi = MultiLineString(lines)
    
    return multi

def multiline_polygon(multiline, buffer=20, density=5):
    """ Given a multilinestring, returns a buffered polygon.
    """
    prepolygon = multiline.buffer(buffer, 3)
    
    if prepolygon.type == 'MultiPolygon':
        geoms = []
        
        for polygon in prepolygon.geoms:
            geom = []
            geom.append(densify_line(polygon.exterior.coords, density))
            geom.append([densify_line(ring.coords, density) for ring in polygon.interiors])
            geoms.append(geom)
        
        polygon = MultiPolygon(geoms)
    else:
        exterior = densify_line(prepolygon.exterior.coords, density)
        interiors = [densify_line(ring.coords, density) for ring in prepolygon.interiors]
        polygon = Polygon(exterior, interiors)
    
    return polygon

def polygon_rings(polygon):
    """ Given a buffer polygon, return a series of point rings.
    """
    if polygon.type == 'Polygon':
        return [polygon.exterior] + list(polygon.interiors)
    
    rings = []
    
    for geom in polygon.geoms:
        rings.append(geom.exterior)
        rings.extend(list(geom.interiors))
    
    return rings

def polygon_skeleton(polygon):
    """ Given a buffer polygon, return a skeleton graph.
    """
    points = []
    
    for ring in polygon_rings(polygon):
        points.extend(list(ring.coords))
    
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
    
    return skeleton

def skeleton_routes(skeleton, min_length=25):
    """ Given a skeleton graph, return a series of (x, y) list routes.
    """
    # it's destructive
    _skeleton = skeleton.copy()
    
    routes = []
    
    while True:
        leaves = [index for index in _skeleton.nodes() if _skeleton.degree(index) == 1]
    
        paths = []
    
        for (v, w) in combinations(leaves, 2):
            try:
                path = shortest_path_length(_skeleton, v, w, 'length'), v, w
            except NetworkXNoPath:
                pass
            else:
                paths.append(path)
    
        if not paths:
            break
        
        paths.sort(reverse=True)
        indexes = shortest_path(_skeleton, paths[0][1], paths[0][2], 'length')

        for (v, w) in zip(indexes[:-1], indexes[1:]):
            _skeleton.remove_edge(v, w)
        
        line = [_skeleton.node[index]['point'] for index in indexes]
        route = [(point.x, point.y) for point in line]
        segments = [LineString([p1, p2]) for (p1, p2) in zip(route[:-1], route[1:])]
        length = sum( [segment.length for segment in segments] )
        
        if length > min_length:
            routes.append(route)
        
        if not _skeleton.edges():
            break
    
    return routes
