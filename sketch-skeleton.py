from sys import exit
from math import pi, sin, cos, tan, atan2, hypot
from operator import attrgetter

from PIL import Image
from PIL.ImageDraw import ImageDraw
from shapely.geometry import Polygon, LineString

def draw_edge(edge, img, drawn):
    """
    """
    if edge in drawn:
        return
    
    draw = ImageDraw(img)
    draw.line([(edge.p1.x, edge.p1.y), (edge.p2.x, edge.p2.y)], fill=(0xCC, 0xCC, 0xCC), width=2)
    
    drawn.add(edge)

def draw_collision(collision, img, drawn):
    """
    """
    if collision in drawn:
        return

    draw_ray(collision.p_ray, img, drawn)
    draw_ray(collision.n_ray, img, drawn)
    
    p = collision.point
    
    draw = ImageDraw(img)
    draw.line([(p.x - 2, p.y - 2), (p.x + 2, p.y + 2)], fill=(0xCC, 0x00, 0x00), width=1)
    draw.line([(p.x - 2, p.y + 2), (p.x + 2, p.y - 2)], fill=(0xCC, 0x00, 0x00), width=1)
    
    drawn.add(collision)

def draw_ray(ray, img, drawn):
    """
    """
    if ray in drawn:
        return
    
    for tail in (ray.p_tail, ray.n_tail):
        draw_tail(tail, img, drawn)
    
    p1 = ray.start
    p2 = Point(p1.x + 10 * cos(ray.theta), p1.y + 10 * sin(ray.theta))
    
    draw = ImageDraw(img)
    draw.rectangle([(p1.x - 1, p1.y - 1), (p1.x + 1, p1.y + 1)], fill=(0xCC, 0x00, 0x00))
    draw.line([(p1.x, p1.y), (p2.x, p2.y)], fill=(0xCC, 0x00, 0x00), width=1)
    
    drawn.add(ray)

def draw_tail(tail, img, drawn):
    """
    """
    if tail in drawn:
        return
    
    for edge in (tail.p_edge, tail.n_edge):
        draw_edge(edge, img, drawn)
    
    for other in tail.tails:
        draw_tail(other, img, drawn)
    
    p1 = tail.start
    p2 = tail.end
    
    draw = ImageDraw(img)
    draw.line([(p1.x, p1.y), (p2.x, p2.y)], fill=(0x00, 0x99, 0xFF), width=1)
    
    drawn.add(tail)

class Point:
    """
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return 'Point ' + ('%x (%.1f, %.1f)' % (id(self), self.x, self.y))[2:]

class Edge:
    """
    """
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        
        self.theta = atan2(p2.y - p1.y, p2.x - p1.x)

class Tail:
    """
    """
    def __init__(self, end, p_edge, n_edge, *tails):
        self.end = end
        self.tails = tails
        self.p_edge = p_edge
        self.n_edge = n_edge
        
        ends = set([tail.end for tail in tails])
        assert len(ends) == 1, 'All the adjoined tails must share a common end'
        
        self.start = tails[0].end
        self.length = max([tail.length for tail in tails])
        self.length += hypot(end.x - self.start.x, end.y - self.start.y)

    def __repr__(self):
        return 'Tail ' + ('%x (%.1f, %s)' % (id(self), self.length, self.is_leaf()))[2:]

    def is_leaf(self):
        return len(self.tails) <= 1
    
class Stub:
    """
    """
    def __init__(self, end, p_edge, n_edge):
        self.end = end
        self.p_edge = p_edge
        self.n_edge = n_edge
        self.length = 0
        
        self.start = end
        self.tails = []

    def __repr__(self):
        return 'Stub ' + ('%x' % id(self))[2:]

    def is_leaf(self):
        return True

class Ray:
    """
    """
    def __init__(self, start, p_tail, n_tail):
        self.start = start
        self.p_tail = p_tail
        self.n_tail = n_tail
        self.theta = self._theta()

    def __repr__(self):
        return 'Ray ' + ('%x' % id(self))[2:]

    def _theta(self):
        n_theta = self.n_tail.n_edge.theta
        p_theta = self.p_tail.p_edge.theta
    
        if abs(tan(n_theta) - tan(p_theta)) < 0.000001:
            # we have parallel edges
            return n_theta

        if n_theta < p_theta:
            n_theta += pi * 2

        rotation = n_theta - p_theta
        
        if rotation > pi:
            rotation -= pi * 2
        
        return p_theta + rotation/2 + pi/2

class Collision:
    """
    """
    def __init__(self, p_ray, n_ray):
        self.p_ray = p_ray
        self.n_ray = n_ray
        
        self.distance, self.point = self._intersection()

    def __repr__(self):
        return 'Collision ' + ('%x' % id(self))[2:]

    def _intersection(self):
        """
        """
        ray1, ray2 = self.p_ray, self.n_ray
        
        is_closure = ray1.p_tail.p_edge is ray2.n_tail.n_edge and ray2.p_tail.p_edge is ray1.n_tail.n_edge
        
        if is_closure:
        
            tails1 = set((ray1.p_tail, ray1.n_tail))
            tails2 = set((ray2.p_tail, ray2.n_tail))
            
            if len(tails2) > len(tails1):
                ray = ray2
            else:
                ray = ray1
        
            return 0, ray.start
        
        x1, y1 = ray1.start.x, ray1.start.y
        sin1, cos1 = sin(ray1.theta), cos(ray1.theta)
    
        x2, y2 = ray2.start.x, ray2.start.y
        sin2, cos2 = sin(ray2.theta), cos(ray2.theta)
        
        # Based on parametric form, where:
        #   x = x1 + cos1 * t
        #   y = y1 + sin1 * t
        #   x = x2 + cos2 * t
        #   y = y2 + sin2 * t
        
        x = (cos2*sin1*x1 - cos2*cos1*y1 - cos1*sin2*x2 + cos1*cos2*y2) / (cos2*sin1 - cos1*sin2)
        y = (sin2*x - sin2*x2 + cos2*y2) / cos2
        
        p1, p2 = ray1.p_tail.p_edge.p1, ray1.p_tail.p_edge.p2
        x1, y1, x2, y2 = p1.x, p1.y, p2.x, p2.y
        
        # see formula 14, http://mathworld.wolfram.com/Point-LineDistance2-Dimensional.html
        d = abs((x2 - x1) * (y1 - y) - (x1 - x) * (y2 - y1)) / hypot(x2 - x1, y2 - y1)
    
        return d, Point(x, y)

def polygon_edges(poly):
    """
    """
    assert poly.__class__ is Polygon, 'Polygon, not MultiPolygon'
    assert len(poly.interiors) == 0, 'No donut holes, either'
    
    points, edges = [], []
    
    for i in range(len(poly.exterior.coords) - 1):
        p = Point(*poly.exterior.coords[i])
        points.append(p)
    
    for (i, p1) in enumerate(points):
        j = (i + 1) % len(points)
        p2 = points[j]
        edge = Edge(p1, p2)
        edges.append(edge)
    
    return edges

def edge_rays(edges):
    """
    """
    stubs, rays = [], []
    
    for (i, edge) in enumerate(edges):
        j = (i + 1) % len(edges)
        stub = Stub(edge.p2, edges[i], edges[j])
        stubs.append(stub)

    for stub in stubs:
        ray = Ray(stub.end, stub, stub)
        rays.append(ray)

    return rays

def ray_collisions(rays):
    """
    """
    collisions = []
    
    for (i, ray1) in enumerate(rays):
        j = (i + 1) % len(rays)
        ray2 = rays[j]
        collision = Collision(ray1, ray2)
        collisions.append(collision)
    
    return collisions

calculated_intersections = {}

def print_rays(rays):
    """
    """
    for ray in rays:
        print ray
        print ' ', ray.start
        
        for tail in set((ray.p_tail, ray.n_tail)):
            print ' ', tail
            print '   ', tail.end

if __name__ == '__main__':
    
    poly = Polygon(((150, 25), (250, 250), (50, 250)))
    poly = Polygon(((140, 25), (160, 25), (250, 100), (250, 250), (50, 250), (40, 240)))
    
    poly = LineString(((50, 50), (200, 50), (250, 100), (250, 250), (50, 250))).buffer(30, 2)
    poly = Polygon(list(reversed(poly.exterior.coords)))
    
    edges = polygon_edges(poly)
    rays = edge_rays(edges)
    collisions = ray_collisions(rays)
    
    print len(edges), 'edges,', len(rays), 'rays,', len(collisions), 'collisions.'
    
    frame = 1
    
    img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
    drawn = set()
    
    for collision in collisions:
        draw_collision(collision, img, drawn)
    
    img.save('skeleton-%03d.png' % frame)

    #print_rays(rays)
    print frame, '-' * 40
    
    while len(collisions) > 1:

        frame += 1
        
        collisions.sort(key=attrgetter('distance'))
        collision = collisions.pop(0)
        
        p_ray = collision.p_ray
        n_ray = collision.n_ray
        point = collision.point
        
        p_tail = Tail(point, p_ray.p_tail.p_edge, p_ray.n_tail.n_edge, p_ray.p_tail, p_ray.n_tail)
        n_tail = Tail(point, n_ray.p_tail.p_edge, n_ray.n_tail.n_edge, n_ray.p_tail, n_ray.n_tail)
        new_ray = Ray(point, p_tail, n_tail)
        
        for old_collision in collisions:
            if old_collision.n_ray is p_ray:
                new_collision = Collision(old_collision.p_ray, new_ray)
                collisions.remove(old_collision)
                collisions.append(new_collision)
            
        for old_collision in collisions:
            if old_collision.p_ray is n_ray:
                new_collision = Collision(new_ray, old_collision.n_ray)
                collisions.remove(old_collision)
                collisions.append(new_collision)
    
        img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
        drawn = set()
        
        for collision in collisions:
            draw_collision(collision, img, drawn)
        
        img.save('skeleton-%03d.png' % frame)
    
        #print_rays(rays)
        print frame, '-' * 40
