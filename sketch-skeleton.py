from sys import exit
from math import pi, sin, cos, atan2

from PIL import Image
from PIL.ImageDraw import ImageDraw
from shapely.geometry import Polygon, LineString

def draw_edge(edge, img):
    """
    """
    draw = ImageDraw(img)
    draw.line([(edge.p1.x, edge.p1.y), (edge.p2.x, edge.p2.y)], fill=(0xCC, 0xCC, 0xCC), width=2)
    
    return img

def draw_ray(ray, img):
    """
    """
    p1 = ray.point
    p2 = Point(p1.x + 10 * cos(ray.theta), p1.y + 10 * sin(ray.theta))
    
    draw = ImageDraw(img)
    draw.rectangle([(p1.x - 1, p1.y - 1), (p1.x + 1, p1.y + 1)], fill=(0xCC, 0x00, 0x00))
    draw.line([(p1.x, p1.y), (p2.x, p2.y)], fill=(0xCC, 0x00, 0x00), width=1)
    
    return img

class Point:
    """
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

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
    def __init__(self, point, p_edge, n_edge, *tails):
        self.point = point
        self.tails = tails
        self.p_edge = p_edge
        self.n_edge = n_edge

    def is_leaf(self):
        return len(self.tails) == 0

class Stub:
    """
    """
    def __init__(self, point, p_edge, n_edge):
        self.point = point
        self.p_edge = p_edge
        self.n_edge = n_edge
        self.theta = self._theta()

    def is_leaf(self):
        return True

    def _theta(self):
        p_theta = self.p_edge.theta + pi/2
        n_theta = self.n_edge.theta + pi/2
        
        pdx, pdy = cos(p_theta), sin(p_theta)
        ndx, ndy = cos(n_theta), sin(n_theta)
        
        dx, dy = (pdx + ndx) / 2, (pdy + ndy) / 2

        theta = atan2(dy, dx)
        
        return theta

class Ray:
    """
    """
    def __init__(self, point, *tails):
        self.point = point
        self.tails = tails
        self.theta = self._theta()
        
        self.next, self.prev = None, None

    def _theta(self):
        thetas = [tail.theta for tail in self.tails]
        
        xs, ys = map(cos, thetas), map(sin, thetas)
        
        dx, dy = sum(xs) / len(xs), sum(ys) / len(ys)
        
        theta = atan2(dy, dx)
        
        return theta

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
        ray = Ray(stub.point, stub)
        rays.append(ray)

    return rays

if __name__ == '__main__':
    
    poly = Polygon(((150, 25), (250, 250), (50, 250)))
    
    edges = polygon_edges(poly)
    rays = edge_rays(edges)
    
    img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
    
    for edge in edges:
        img = draw_edge(edge, img)
    
    for ray in rays:
        img = draw_ray(ray, img)

    #exit(1)
    
    img.save('skeleton.png')
