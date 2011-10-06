from time import sleep
from math import hypot, ceil, pi
from xml.parsers.expat import ParserCreate
from subprocess import Popen, PIPE
from itertools import combinations
    
from cairo import Context, ImageSurface, FORMAT_RGB24, LINE_CAP_ROUND
from shapely.geometry import Point, LineString, Polygon, MultiLineString, MultiPolygon
from networkx.algorithms.shortest_paths.generic import shortest_path, shortest_path_length
from networkx.exception import NetworkXNoPath
from networkx import Graph
from pyproj import Proj

merc = Proj('+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over')

def way_key(tags):
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

    def __init__(self):
        self.p = ParserCreate()
        self.p.StartElementHandler = self.start_element
        self.p.EndElementHandler = self.end_element
        #self.p.CharacterDataHandler = char_data
    
    def parse(self, input):
        self.nodes = dict()
        self.ways = dict()
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
        key = way_key(way['tags'])
        
        if key:
            way['key'] = key
            del way['tags']

        else:
            del self.ways[self.way]
        
        self.way = None

class Canvas:

    def __init__(self, width, height):
        self.xform = lambda x, y: (x, y)
    
        self.img = ImageSurface(FORMAT_RGB24, width, height)
        self.ctx = Context(self.img)
        
        self.ctx.move_to(0, 0)
        self.ctx.line_to(width, 0)
        self.ctx.line_to(width, height)
        self.ctx.line_to(0, height)
        self.ctx.line_to(0, 0)
        
        self.ctx.set_source_rgb(1, 1, 1)
        self.ctx.fill()
        
        self.width = width
        self.height = height
    
    def fit(self, left, top, right, bottom):
        xoff = left
        yoff = top
        
        xscale = self.width / (right - left)
        yscale = self.height / (bottom - top)
        
        if abs(xscale) > abs(yscale):
            xscale *= abs(yscale) / abs(xscale)
        
        elif abs(xscale) < abs(yscale):
            yscale *= abs(xscale) / abs(yscale)

        self.xform = lambda x, y: ((x - xoff) * xscale, (y - yoff) * yscale)
    
    def dot(self, x, y, size=4, fill=(.5, .5, .5)):
        x, y = self.xform(x, y)

        self.ctx.arc(x, y, size/2., 0, 2*pi)
        self.ctx.set_source_rgb(*fill)
        self.ctx.fill()
    
    def line(self, points, stroke=(.5, .5, .5), width=1):
        self.ctx.move_to(*self.xform(*points[0]))
        
        for (x, y) in points[1:]:
            self.ctx.line_to(*self.xform(x, y))
        
        self.ctx.set_source_rgb(*stroke)
        self.ctx.set_line_cap(LINE_CAP_ROUND)
        self.ctx.set_line_width(width)
        self.ctx.stroke()
    
    def save(self, filename):
        self.img.write_to_png(filename)

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

def densify(ring, distance):
    """
    """
    coords = [ring.coords[0]]
    
    for curr_coord in list(ring.coords)[1:]:
        prev_coord = coords[-1]
    
        dx, dy = curr_coord[0] - prev_coord[0], curr_coord[1] - prev_coord[1]
        steps = ceil(hypot(dx, dy) / distance)
        count = int(steps)
        
        while count:
            prev_coord = prev_coord[0] + dx/steps, prev_coord[1] + dy/steps
            coords.append(prev_coord)
            count -= 1
    
    return coords

def buffer_graph(graph):
    lines = [(graph.node[a]['point'], graph.node[b]['point']) for (a, b) in graph.edges()]
    lines = [((p1.x, p1.y), (p2.x, p2.y)) for (p1, p2) in lines]
    lines = MultiLineString(lines)
    lines = lines.buffer(20, 3)
    
    if lines.type == 'MultiPolygon':
        geoms = []
        
        for poly in lines.geoms:
            geom = []
            geom.append(densify(poly.exterior, 5))
            geom.append([densify(ring, 5) for ring in poly.interiors])
            geoms.append(geom)
        
        poly = MultiPolygon(geoms)
    else:
        exterior = densify(lines.exterior, 5)
        interiors = [densify(ring, 5) for ring in lines.interiors]
        poly = Polygon(exterior, interiors)
    
    return poly

def polygon_rings(polygon):
    if polygon.type == 'Polygon':
        return [polygon.exterior] + list(polygon.interiors)
    
    rings = []
    
    for geom in polygon.geoms:
        rings.append(geom.exterior)
        rings.extend(list(geom.interiors))
    
    return rings

def skeleton_graph(polygon):
    points = []
    
    for ring in polygon_rings(polygon):
        points.extend(list(ring.coords))
    
    print 'qhull...'
    
    rbox = '\n'.join( ['2', str(len(points))] + ['%.2f %.2f' % (x, y) for (x, y) in points] + [''] )
    
    qhull = Popen('qvoronoi o'.split(), stdin=PIPE, stdout=PIPE)
    qhull.stdin.write(rbox)
    qhull.stdin.close()
    sleep(1) # qhull.wait()
    qhull = qhull.stdout.read().splitlines()
    
    vert_count, poly_count = map(int, qhull[1].split()[:2])
    
    print 'graph...'
    
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
    
    print 'trim...'
    
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

def graph_routes(graph):
    """
    """
    # it's destructive
    graph = graph.copy()
    
    routes = []
    
    while True:
        leaves = [index for index in graph.nodes() if graph.degree(index) == 1]
    
        paths = []
    
        for (v, w) in combinations(leaves, 2):
            try:
                path = shortest_path_length(graph, v, w, 'length'), v, w
            except NetworkXNoPath:
                pass
            else:
                paths.append(path)
    
        if not paths:
            break
        
        paths.sort(reverse=True)
        indexes = shortest_path(graph, paths[0][1], paths[0][2], 'length')

        for (v, w) in zip(indexes[:-1], indexes[1:]):
            graph.remove_edge(v, w)
        
        line = [graph.node[index]['point'] for index in indexes]
        route = [(point.x, point.y) for point in line]
        routes.append(route)
        
        if not graph.edges():
            break
    
    return routes
