from time import sleep
from math import hypot, ceil, pi
from xml.parsers.expat import ParserCreate
from subprocess import Popen, PIPE

from cairo import Context, ImageSurface, FORMAT_RGB24
from shapely.geometry import Point, LineString, Polygon, MultiLineString, MultiPolygon
from networkx import Graph
from pyproj import Proj

merc = Proj('+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over')

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
            key = tuple(way['key'])
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
        self.ways[id] = dict(nodes=[], key=[None, None])
    
    def tag_way(self, key, value):
        way = self.ways[self.way]

        if key == 'name':
            way['key'][0] = value
        elif key == 'highway':
            way['key'][1] = value
    
    def extend_way(self, id):
        way = self.ways[self.way]
        way['nodes'].append(id)
    
    def end_way(self):
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
    
    def dot(self, x, y, size=2, fill=(.5, .5, .5)):
        x, y = self.xform(x, y)

        self.ctx.arc(x, y, size/2., 0, 2*pi)
        self.ctx.set_source_rgb(*fill)
        self.ctx.fill()
    
    def line(self, points, stroke=(.5, .5, .5), width=1):
        self.ctx.move_to(*self.xform(*points[0]))
        
        for (x, y) in points[1:]:
            self.ctx.line_to(*self.xform(x, y))
    
        self.ctx.set_source_rgb(*stroke)
        self.ctx.set_line_width(width)
        self.ctx.stroke()
    
    def save(self, filename):
        self.img.write_to_png(filename)

def segmentize(ring, distance):
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
        raise Exception('not yet')
        geoms = []
        
        for poly in lines.geoms:
            geom = []
            geom.append(segmentize(poly.exterior, 5))
    else:
        exterior = segmentize(lines.exterior, 5)
        interiors = [segmentize(ring, 5) for ring in lines.interiors]
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
