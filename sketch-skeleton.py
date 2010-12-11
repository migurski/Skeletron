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

    def rays(self):
        """
        """
        p1, p2 = self.p1, self.p2
        theta = atan2(p2.y - p1.y, p2.x - p1.x)
        
        ray1 = Ray(p1, theta + pi/2)
        ray2 = Ray(p2, theta + pi/2)
        
        return ray1, ray2

class Ray:
    """
    """
    def __init__(self, point, theta, floor=0):
        self.point = point
        self.theta = theta
        self.floor = floor

def merge_rays(r1, r2):
    """
    """
    pass

def polygon_edges(poly):
    """
    """
    assert poly.__class__ is Polygon, 'Polygon, not MultiPolygon'
    assert len(poly.interiors) == 0, 'No donut holes, either'
    
    edges = []
    
    for i in range(len(poly.exterior.coords) - 1):
        p1 = Point(*poly.exterior.coords[i])
        p2 = Point(*poly.exterior.coords[i + 1])
        edges.append(Edge(p1, p2))
    
    return edges

if __name__ == '__main__':
    
    poly = Polygon(((150, 25), (250, 250), (50, 250)))
    
    edges = polygon_edges(poly)
    
    img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
    
    for edge in edges:
        img = draw_edge(edge, img)
    
    for edge in edges:
        for ray in edge.rays():
            img = draw_ray(ray, img)
    
    #exit(1)
    
    img.save('skeleton.png')
