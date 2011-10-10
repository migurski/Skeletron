from time import sleep
from math import hypot, ceil
from subprocess import Popen, PIPE
from itertools import combinations
    
from shapely.geometry import Point, LineString, Polygon, MultiLineString, MultiPolygon
from networkx.algorithms.shortest_paths.generic import shortest_path, shortest_path_length
from networkx.exception import NetworkXNoPath
from networkx import Graph

def simplify_line(points, small_area=100):
    """ Simplify a line of points using V-W down to the given area.
    """
    if len(points) < 3:
        return list(points)

    while True:
        
        # For each coordinate that forms the apex of a two-segment
        # triangle, find the area of that triangle and put it into a list
        # along with the index, ordered from smallest to largest.
    
        popped, preserved = set(), set()
        
        triples = zip(points[:-2], points[1:-1], points[2:])
        triangles = [Polygon((p1, p2, p3)) for (p1, p2, p3) in triples]
        areas = [(triangle.area, index) for (index, triangle) in enumerate(triangles)]
        
        # Reduce any segments that makes a triangle whose area is below
        # the minimum threshold, starting with the smallest and working up.
        # Mark segments to be preserved until the next iteration.

        for (area, index) in sorted(areas):
            if area > small_area:
                # nothing more can be removed on this iteration
                break
            
            if (index + 1) in preserved:
                # current index is too close to a previously-preserved one
                continue
            
            preserved.add(index)
            popped.add(index + 1)
            preserved.add(index + 2)
        
        if not popped:
            # nothing was removed so we are done
            break
        
        # reduce the line, then try again
        points = [point for (index, point) in enumerate(points) if index not in popped]
    
    return points

def densify_line(points, distance):
    """ Densify a line of points using the given distance.
    """
    coords = [points[0]]
    
    for curr_coord in list(points)[1:]:
        prev_coord = coords[-1]
    
        dx, dy = curr_coord[0] - prev_coord[0], curr_coord[1] - prev_coord[1]
        steps = ceil(hypot(dx, dy) / distance)
        count = int(steps)
        
        while count:
            prev_coord = prev_coord[0] + dx/steps, prev_coord[1] + dy/steps
            coords.append(prev_coord)
            count -= 1
    
    return coords

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
    
    qhull = Popen('qvoronoi o'.split(), stdin=PIPE, stdout=PIPE)
    qhull.stdin.write(rbox)
    qhull.stdin.close()
    sleep(.1) # this was once necessary, why?
    qhull.wait()
    qhull = qhull.stdout.read().splitlines()
    
    vert_count, poly_count = map(int, qhull[1].split()[:2])
    
    skeleton = Graph()
    
    for (index, line) in enumerate(qhull[2:2+vert_count]):
        point = Point(*map(float, line.split()[:2]))
        if point.within(polygon):
            skeleton.add_node(index, dict(point=point))
    
    for line in qhull[2 + vert_count:2 + vert_count + poly_count]:
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
