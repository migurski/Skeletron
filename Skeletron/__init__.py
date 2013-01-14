""" Linework generalizer for use on maps.

Skeletron generalizes collections of lines to a specific spherical mercator
zoom level and pixel precision, using a polygon buffer and voronoi diagram as
described in a 1996 paper by Alnoor Ladak and Roberto B. Martinez, "Automated
Derivation of High Accuracy Road Centrelines Thiessen Polygons Technique"
(http://proceedings.esri.com/library/userconf/proc96/TO400/PAP370/P370.HTM).

Required dependencies:
  - qhull binary (http://www.qhull.org)
  - shapely (http://pypi.python.org/pypi/Shapely)
  - pyproj (http://code.google.com/p/pyproj)
  - networkx (http://networkx.lanl.gov)

You'd typically use it via one of the provided utility scripts, currently
just these three:

skeletron-generalize.py

  Accepts GeoJSON input and generates GeoJSON output.

skeletron-osm-streets.py

  Accepts OpenStreetMap XML input and generates GeoJSON output for streets
  using the "name" and "highway" tags to group collections of ways.

skeletron-osm-route-rels.py

  Accepts OpenStreetMap XML input and generates GeoJSON output for routes
  using the "network", "ref" and "modifier" tags to group relations.
  More on route relations: http://wiki.openstreetmap.org/wiki/Relation:route
"""
__version__ = '0.8.0'

from subprocess import Popen, PIPE
from itertools import combinations
from tempfile import mkstemp
from os import write, close
from math import sin, cos, pi
from math import ceil, atan2
from time import time

from threading import Timer
from thread import interrupt_main

import logging
    
import numpy, numpy.linalg
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

from .util import simplify_line_vw, simplify_line_dp, densify_line, \
                  polygon_rings, cascaded_union, point_distance

class _QHullFailure (Exception): pass
class _SignalAlarm (Exception): pass

class _GraphRoutesOvertime (Exception):
    def __init__(self, graph):
        self.graph = graph

def timeout():
    interrupt_main()

def _buffered_multiline_polygon(multiline, buffer):
    ''' Return a polygon shell with the given buffer around a multiline.
    '''
    lines = multiline.geoms
    pre_count = sum([len(line.coords) for line in lines])
    
    lines = [simplify_line_dp(list(line.coords), buffer) for line in lines]
    count = sum([len(line) for line in lines])

    logging.debug('simplified %d points to %d in %d linestrings' % (pre_count, count, len(lines)))
    
    multiline = MultiLineString(lines)
    return multiline_polygon(multiline, buffer)

def _buffered_multipoly_polygon(multipoly, buffer):
    ''' Return a polygon shell with the given buffer around a multipolygon.
    '''
    polygons = []
    pre_count, count = 0, 0
    
    for poly in multipoly.geoms:
        rings = [poly.exterior] + list(poly.interiors)
        pre_count += sum([len(ring.coords) for ring in rings])
        
        lines = [simplify_line_dp(list(ring.coords), buffer) for ring in rings]
        count += sum([len(line) for line in lines])
        
        polygons.append(Polygon(rings[0], rings[1:]))

    logging.debug('simplified %d points to %d in %d polygons' % (pre_count, count, len(polygons)))
    
    polygons = [poly.buffer(buffer, 3) for poly in polygons]
    return cascaded_union(polygons)

def multigeom_centerline(multigeom, buffer=20, density=10, min_length=40, min_area=100):
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
            generalization by util.simplify_line_vw(), should be approximately
            one quarter of buffer squared.
    """
    if not multigeom:
        return False
    
    if multigeom.type == 'MultiLineString':
        buffered = _buffered_multiline_polygon(multigeom, buffer)
        
    elif multigeom.type == 'MultiPolygon':
        buffered = _buffered_multipoly_polygon(multigeom, buffer)
    
    else:
        raise ValueError(multigeom.type)
    
    lines, points = [], 0
    
    #
    # Iterate over each constituent buffer polygon, extending the skeleton.
    #
    
    for polygon in getattr(buffered, 'geoms', [buffered]):
        try:
            skeletons = polygon_skeleton_graphs(polygon, buffer, density)
        
        except _QHullFailure, e:
            #
            # QHull failures here are usually signs of tiny geometries,
            # so they are usually fine to ignore completely and move on.
            #
            logging.error('QHull failure: %s' % e)
            
            handle, fname = mkstemp(dir='.', prefix='qhull-failure-', suffix='.txt')
            write(handle, 'Error: %s\nDensity: %.6f\nPolygon: %s\n' % (e, density, str(polygon)))
            close(handle)
            continue
        
        try:
            routes = skeleton_routes(skeletons, min_length)

        except _SignalAlarm, e:
            # An alarm signal here means that graph_routes() went overtime.
            raise _GraphRoutesOvertime(skeletons)
        
        points += sum(map(len, routes))
        lines.extend([simplify_line_vw(route, min_area) for route in routes])
    
    logging.debug('selected %d final points from %d graph route points' % (sum(map(len, lines)), points))
    
    if not lines:
        return False
    
    return MultiLineString(lines)

def graph_routes(graph, find_longest, time_coefficient=0.02):
    """ Return a list of routes through a network as (x, y) pair lists, with no edge repeated.
    
        Use a thread timer to check for time overruns; see _graph_routes_main()
        for in-thread logic.
    """
    #
    # Before we do anything else, set a time limit to deal with the occasional
    # halting problem on larger graphs. Use a threading Timer to check time.
    #
    time_limit = int(ceil(time_coefficient * graph.number_of_nodes()))

    try:
        t = Timer(time_limit, timeout)
        t.start()
        routes = _graph_routes_main(graph, find_longest, time_coefficient)
        t.cancel()
        return routes
    
    except:
        t.cancel()
        raise _SignalAlarm('Timeout')

def _graph_routes_main(graph, find_longest, time_coefficient=0.02):
    """ Return a list of routes through a network as (x, y) pair lists, with no edge repeated.
    
        Called from graph_routes().
    
        Each node in the graph must have a "point" attribute with a Point object.
        
        The time_coefficient argument helps determine a time limit after which
        this function is killed off by means of a SIGALRM. With the addition of
        divide_points() in polygon_skeleton_graphs() as of version 0.6.0, this
        condition is much less likely to actually happen.

        The default value of 0.02 comes from a graph of times for a single
        state's generalized routes at a few zoom levels. I found that this
        function typically runs in O(n) time best case with some spikes up
        to O(n^2) and a general cluster around O(n^1.32). Introducing a time
        limit based on O(n^2) seemed too generous for large graphs, while
        the coefficient 0.02 seemed to comfortably cover graphs with up to
        tens of thousands of nodes.
        
        In the graph (new-hampshire-times.png) the functions are:
        - X-axis: graph size in nodes
        - Y-axis: compute time in seconds
        - Orange dashed good-enough limit: y = 0.02x
        - Blue bottom limit: y = 0.00005x
        - Green trend line: y = 2.772e-5x^1.3176
        - Black upper bounds: y = 0.000001x^2
    """
    # it's destructive
    _graph = graph.copy()
    
    start_nodes, start_time = _graph.number_of_nodes(), time()
    
    # passed directly to shortest_path()
    weight = find_longest and 'length' or None
    
    # heuristic function for A* path-finding functions, see also:
    # http://networkx.lanl.gov/reference/algorithms.shortest_paths.html#module-networkx.algorithms.shortest_paths.astar
    heuristic = lambda n1, n2: point_distance(_graph.node[n1]['point'], _graph.node[n2]['point'])
    
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

        distances = [(point_distance(_graph.node[v]['point'], _graph.node[w]['point']), v, w)
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
    
    print >> open('graph-routes-log.txt', 'a'), start_nodes, (time() - start_time)

    return routes

def waynode_multilines(ways, nodes):
    """ Convert dictionaries of ways and nodes to dictionary of multilines.
    """
    multilines = dict()
    
    for way in ways.values():
        key = way['key']
        node_ids = way['nodes']
        
        if len(node_ids) < 2:
            continue
        
        if key not in multilines:
            multilines[key] = []
        
        points = [mercator(*reversed(nodes[id])) for id in node_ids]
        multilines[key].append(LineString(points))
    
    for (key, lines) in multilines.items():
        lines = [list(line.coords) for line in lines]
        multilines[key] = MultiLineString(lines)
    
    return multilines

def _m(geom):
    ''' Project the coordinates of a geometry such as a line or ring.
    '''
    return [mercator(x, y) for (x, y) in geom.coords]

def projected_multigeometry(geom):
    ''' Accept an unprojected geometry and return a projected multigeometry.
    '''
    geoms = getattr(geom, 'geoms', [geom])
    
    if geom.type in ('LineString', 'MultiLineString'):
        projected = MultiLineString(map(_m, geoms))
    
    elif geom.type in ('Polygon', 'MultiPolygon'):
        parts = [(_m(poly.exterior), map(_m, poly.interiors)) for poly in geoms]
        projected = MultiPolygon(parts)
    
    else:
        raise ValueError("Can't generalize a %s geometry" % geom.type)
    
    return projected

def geometry_multiline(geom):
    '''
    '''
    if geom.type not in ('LineString', 'MultiLineString'):
        raise ValueError("Can't generalize a %s geometry" % geom.type)
    
    geoms = geom.geoms if hasattr(geom, 'geoms') else [geom]
    coords = [[mercator(x, y) for (x, y) in line.coords] for line in geoms]
    projected = MultiLineString(coords)
    
    return projected

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
    return cascaded_union(polys)

def polygon_skeleton_graphs(polygon, buffer=20, density=10):
    """ Given a buffer polygon, return a list of skeleton graphs.
    """
    points = []
    
    #
    # Build up a list of points by densifying the perimeter of each part
    # of the polygon, resulting in a possibly lengthy list of (x, y) pairs.
    #
    for ring in polygon_rings(polygon):
        points.extend(densify_line(list(ring.coords), density))
    
    if len(points) <= 4:
        # Don't bother with very short lists of points.
        return Graph()
    
    max_points = 5000

    if len(points) < max_points:
        # Don't subdivide point collections smaller than max_points.
        return [polygon_dots_skeleton(polygon, points)]
    
    point_lists = [points]
    skeletons = []
    
    #
    # Subdivide large collections of points along their
    # major axes, and make a skeleton for each subdivision.
    #
    while point_lists:
        points1, points2, poly1, poly2 = divide_points(point_lists.pop(0))
        
        logging.debug('split %d points into %d + %d' % (len(points1 + points2), len(points1), len(points2)))
        
        for (_points, _poly) in ((points1, poly1), (points2, poly2)):
            if len(_points) < max_points:
                _poly = _poly.buffer(buffer, 3).intersection(polygon)
                skeletons.append(polygon_dots_skeleton(_poly, _points))
            else:
                point_lists.append(_points)
    
    return skeletons

def divide_points(points):
    ''' Divide a list of (x, y) tuples into two lists and two bounding polygons.
    
        Use eigenvectors to determine the major axis and split on it,
        at the center (average) of the input point collection.
        
        Eigenbusiness cribbed from
        http://stackoverflow.com/questions/7059841/estimating-aspect-ratio-of-a-convex-hull
    '''
    # Make an array of points and find its average.
    xys = numpy.vstack(points).T
    xcenter, ycenter = (xys / len(points)).sum(1)

    # Calculate angle of major axis.
    eigvals, eigvecs = numpy.linalg.eig(numpy.cov(xys))
    (x, y) = sorted(zip(eigvals, eigvecs.T))[-1][1]
    theta = atan2(y, x)
    
    # Translate and rotate points for easy division.
    translate = numpy.vstack([(xcenter, ycenter)] * len(points)).T
    rotate = numpy.array([[cos(theta), sin(theta)], [-sin(theta), cos(theta)]])
    unrotate = numpy.array([[cos(-theta), sin(-theta)], [-sin(-theta), cos(-theta)]])
    xys = numpy.dot(rotate, xys - translate)

    #
    # Now, xys is an array of points with the center at (0, 0) and rotated
    # so that the major axis is horizonal, so it's probably safe to cut it
    # in half at x=0 and operate the two sides independently.
    #
    points1 = [(x, y) for (x, y) in xys.T if x < 0]
    points2 = [(x, y) for (x, y) in xys.T if x >= 0]
    
    (xmin, ymin), (xmax, ymax) = xys.min(1), xys.max(1)
    
    bbox1 = numpy.array([(0, ymin), (0, ymax), (xmin, ymax), (xmin, ymin)]).T
    bbox2 = numpy.array([(0, ymin), (0, ymax), (xmax, ymax), (xmax, ymin)]).T
    
    # Return points to original positions in two groups.
    translate1 = numpy.vstack([(xcenter, ycenter)] * len(points1)).T
    translate2 = numpy.vstack([(xcenter, ycenter)] * len(points2)).T

    xys1 = numpy.dot(unrotate, numpy.vstack(points1).T) + translate1
    xys2 = numpy.dot(unrotate, numpy.vstack(points2).T) + translate2
    
    points1 = [(x, y) for (x, y) in xys1.T]
    points2 = [(x, y) for (x, y) in xys2.T]
    
    bbox1 = numpy.dot(unrotate, bbox1) + translate1[:,:4]
    bbox2 = numpy.dot(unrotate, bbox2) + translate2[:,:4]
    
    polygon1 = Polygon([(x, y) for (x, y) in bbox1.T])
    polygon2 = Polygon([(x, y) for (x, y) in bbox2.T])
    
    return points1, points2, polygon1, polygon2

def polygon_dots_skeleton(polygon, points):
    '''
    '''
    skeleton = Graph()

    rbox = '\n'.join( ['2', str(len(points))] + ['%.2f %.2f' % (x, y) for (x, y) in points] + [''] )
    
    qvoronoi = Popen('qvoronoi o'.split(), stdin=PIPE, stdout=PIPE)
    output, error = qvoronoi.communicate(rbox)
    voronoi_lines = output.splitlines()
    
    if qvoronoi.returncode:
        raise _QHullFailure('Failed with code %s' % qvoronoi.returncode)
    
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
    
    logging.debug('found %d skeleton edges' % len(skeleton.edge))
    
    return skeleton

def skeleton_routes(skeletons, min_length=25):
    """ Given a list of skeleton graphs, return a series of (x, y) list routes ordered longest to shortest.
    """
    routes = []
    
    for skeleton in skeletons:
        routes.extend(graph_routes(skeleton, True))
    
    return [route for route in routes if LineString(route).length > min_length]
