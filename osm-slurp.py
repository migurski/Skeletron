from sys import stdin
from math import hypot, ceil

from shapely.geometry import Polygon

from Skeletron2 import ParserOSM, Canvas, buffer_graph, polygon_rings, skeleton_graph

p = ParserOSM()
g = p.parse(stdin.read())
print sorted(g.keys())
graph = g[(u'Lakeside Drive', u'secondary')]

# draw the underlying street

points = [graph.node[id]['point'] for id in graph.nodes()]
xs, ys = map(None, *[(pt.x, pt.y) for pt in points])

xmin, ymin, xmax, ymax = min(xs), min(ys), max(xs), max(ys)

canvas = Canvas(900, 600)
canvas.fit(xmin - 50, ymax + 50, xmax + 50, ymin - 50)

for point in points:
    canvas.dot(point.x, point.y, fill=(.8, .8, .8))

for (a, b) in graph.edges():
    pt1, pt2 = graph.node[a]['point'], graph.node[b]['point']
    line = [(pt1.x, pt1.y), (pt2.x, pt2.y)]
    canvas.line(line, stroke=(.8, .8, .8))

# fatten

poly = buffer_graph(graph)

for ring in polygon_rings(poly):
    canvas.line(list(ring.coords), stroke=(.9, .9, .9))

skeleton = skeleton_graph(poly)

for index in skeleton.nodes():
    point = skeleton.node[index]['point']
    canvas.dot(point.x, point.y)

for (v, w) in skeleton.edges():
    line = list(skeleton.edge[v][w]['line'].coords)
    canvas.line(line)

# find paths

from networkx.algorithms.shortest_paths.generic import shortest_path, shortest_path_length
from networkx.exception import NetworkXNoPath
from itertools import combinations

def simplify(points, small_area=100):
    """
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

for color in [(0, 0, 0), (.7, 0, 0), (1, .2, 0), (1, .6, 0), (1, 1, 0)]:

    leaves = [index for index in skeleton.nodes() if skeleton.degree(index) == 1]

    paths = []

    for (a, b) in combinations(leaves, 2):
        try:
            path = shortest_path_length(skeleton, a, b, 'length'), a, b
        except NetworkXNoPath:
            pass
        else:
            paths.append(path)

    paths.sort(reverse=True)
    indexes = shortest_path(skeleton, paths[0][1], paths[0][2], 'length')
    line = [skeleton.node[index]['point'] for index in indexes]
    line = simplify([(point.x, point.y) for point in line])
    
    canvas.line(line, stroke=color, width=4)
    for (x, y) in line:
        canvas.dot(x, y, fill=color, size=8)
    
    for (v, w) in zip(indexes[:-1], indexes[1:]):
        skeleton.remove_edge(v, w)
    
    if not skeleton.edges():
        break

canvas.save('look.png')
