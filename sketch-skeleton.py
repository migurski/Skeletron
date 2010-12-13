from sys import exit
from math import pi, sin, cos, atan2, hypot

from PIL import Image
from PIL.ImageDraw import ImageDraw
from shapely.geometry import Polygon, LineString
from sympy import Symbol, solve

def draw_edge(edge, img):
    """
    """
    draw = ImageDraw(img)
    draw.line([(edge.p1.x, edge.p1.y), (edge.p2.x, edge.p2.y)], fill=(0xCC, 0xCC, 0xCC), width=2)
    
    return img

def draw_ray(ray, img):
    """
    """
    for tail in set((ray.p_tail, ray.n_tail)):
        draw_tail(tail, img)
    
    p1 = ray.start
    p2 = Point(p1.x + 10 * cos(ray.theta), p1.y + 10 * sin(ray.theta))
    
    draw = ImageDraw(img)
    draw.rectangle([(p1.x - 1, p1.y - 1), (p1.x + 1, p1.y + 1)], fill=(0xCC, 0x00, 0x00))
    draw.line([(p1.x, p1.y), (p2.x, p2.y)], fill=(0xCC, 0x00, 0x00), width=1)
    
    return img

def draw_tail(tail, img):
    """
    """
    for other in tail.tails:
        img = draw_tail(other, img)
    
    p1 = tail.start
    p2 = tail.end
    
    draw = ImageDraw(img)
    draw.line([(p1.x, p1.y), (p2.x, p2.y)], fill=(0x00, 0x99, 0xFF), width=1)
    
    return img

class Point:
    """
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return 'Point ' + ('%x (%.1f, %.1f)' % (id(self), self.x, self.y))[4:]

class Edge:
    """
    """
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        
        self.theta = atan2(p2.y - p1.y, p2.x - p1.x)

    def rays(self):
        """
        """
        p1, p2 = self.p1, self.p2
        theta = atan2(p2.y - p1.y, p2.x - p1.x)
        
        ray1 = Ray(p1, theta + pi/2)
        ray2 = Ray(p2, theta + pi/2)
        
        return ray1, ray2

class Tail:
    """
    """
    def __init__(self, end, p_edge, n_edge, *tails):
        self.end = end
        self.tails = tails
        self.p_edge = p_edge
        self.n_edge = n_edge
        self.theta = self._theta()
        
        ends = set([tail.end for tail in tails])
        assert len(ends) == 1, 'All the adjoined tails must share a common end'
        
        self.start = tails[0].end
        self.length = max([tail.length for tail in tails])
        self.length += hypot(end.x - self.start.x, end.y - self.start.y)

    def __repr__(self):
        return 'Tail ' + ('%x (%.1f, %s)' % (id(self), self.length, self.is_leaf()))[4:]

    def is_leaf(self):
        return len(self.tails) <= 1
    
    def _theta(self):
        thetas = [tail.theta for tail in self.tails]
        return average_thetas(thetas)
    
class Stub:
    """
    """
    def __init__(self, end, p_edge, n_edge):
        self.end = end
        self.p_edge = p_edge
        self.n_edge = n_edge
        self.length = 0
        self.theta = self._theta()
        
        self.start = end
        self.tails = []

    def __repr__(self):
        return 'Stub ' + ('%x' % id(self))[4:]

    def is_leaf(self):
        return True

    def _theta(self):
        p_theta = self.p_edge.theta + pi/2
        n_theta = self.n_edge.theta + pi/2
        return average_thetas((p_theta, n_theta))

class Ray:
    """
    """
    def __init__(self, start, p_tail, n_tail):
        self.start = start
        self.p_tail = p_tail
        self.n_tail = n_tail
        self.theta = self._theta()

    def __repr__(self):
        return 'Ray ' + ('%x' % id(self))[4:]

    def _theta(self):
        n_theta = self.n_tail.n_edge.theta
        p_theta = self.p_tail.p_edge.theta + pi
        thetas = n_theta, p_theta
        return average_thetas(thetas)

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
    
    for (j, edge) in enumerate(edges):
        i = (j - 1) % len(edges)
        stub = Stub(edge.p1, edges[i], edges[j])
        stubs.append(stub)

    for stub in stubs:
        ray = Ray(stub.end, stub, stub)
        rays.append(ray)

    return rays

def rays_intersection(ray1, ray2):
    """
    """
    if ray1.p_tail.p_edge is ray2.n_tail.n_edge and ray2.p_tail.p_edge is ray1.n_tail.n_edge:
    
        tails1 = set((ray1.p_tail, ray1.n_tail))
        tails2 = set((ray2.p_tail, ray2.n_tail))
        
        if len(tails2) > len(tails1):
            ray = ray2
        else:
            ray = ray1
    
        return 0, ray.start, ray1, ray2
    
    x, y = Symbol('x'), Symbol('y')
    
    x1, y1 = ray1.start.x, ray1.start.y
    s1, c1 = sin(ray1.theta), cos(ray1.theta)

    x2, y2 = ray2.start.x, ray2.start.y
    s2, c2 = sin(ray2.theta), cos(ray2.theta)
    
    # Based on parametric form, where:
    #   x = x1 + c1 * t
    #   y = y1 + s1 * t
    #   x = x2 + c2 * t
    #   y = y2 + s2 * t
    
    a1 = s1
    b1 = -c1
    c1 = c1 * y1 - s1 * x1

    a2 = s2
    b2 = -c2
    c2 = c2 * y2 - s2 * x2
    
    solution = solve((a1 * x + b1 * y + c1, a2 * x + b2 * y + c2), x, y)
    
    if solution is None:
        return 6378000, None, ray1, ray2
    
    x, y = solution[x], solution[y]
    
    d1 = hypot(x - x1, y - y1)
    d2 = hypot(x - x2, y - y2)
    
    return min(d1, d2), Point(x, y), ray1, ray2

def print_rays(rays):
    """
    """
    for ray in rays:
        print ray
        print ' ', ray.start
        
        for tail in set((ray.p_tail, ray.n_tail)):
            print ' ', tail
            print '   ', tail.end

def paired(things):
    """
    """
    for (i, thing1) in enumerate(things):
        j = (i + 1) % len(things)
        thing2 = things[j]
        
        yield (thing1, thing2)

def average_thetas(thetas):
    """
    """
    xs, ys = map(cos, thetas), map(sin, thetas)

    dx, dy = sum(xs) / len(xs), sum(ys) / len(ys)
    
    theta = atan2(dy, dx)
    return theta

if __name__ == '__main__':
    
    poly = LineString(((50, 50), (200, 50), (250, 100), (250, 250), (50, 250))).buffer(30, 2)
    poly = Polygon(list(reversed(poly.exterior.coords)))
    
    poly = Polygon(((150, 25), (250, 250), (50, 250)))
    poly = Polygon(((140, 25), (160, 25), (250, 100), (250, 250), (50, 250), (40, 240)))
    
    edges = polygon_edges(poly)
    rays = edge_rays(edges)
    
    frame = 1
    
    while len(rays) > 1:
    
        img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
        
        for edge in edges:
            img = draw_edge(edge, img)
    
        for ray in rays:
            img = draw_ray(ray, img)
        
        img.save('skeleton-%03d.png' % frame)
    
        #print_rays(rays)
        print frame, '-' * 40
        
        intersections = [rays_intersection(ray1, ray2) for (ray1, ray2) in paired(rays)]
        intersections = sorted(intersections)
        distance, point, ray1, ray2 = intersections[0]
        
        p_tail = Tail(point, ray1.p_tail.p_edge, ray1.n_tail.n_edge, ray1.p_tail, ray1.n_tail)
        n_tail = Tail(point, ray2.p_tail.p_edge, ray2.n_tail.n_edge, ray2.p_tail, ray2.n_tail)
        nu_ray = Ray(point, p_tail, n_tail)
        
        nu_rays = []
        
        for ray in rays:
            if ray is ray1:
                nu_rays.append(nu_ray)
            elif ray is ray2:
                pass
            else:
                nu_rays.append(ray)
    
        rays = nu_rays
        frame += 1

    img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
    
    for edge in edges:
        img = draw_edge(edge, img)

    for ray in rays:
        img = draw_ray(ray, img)
    
    img.save('skeleton-%03d.png' % frame)

    #print_rays(rays)
    print frame, '=' * 40
