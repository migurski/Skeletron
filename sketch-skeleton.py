from math import pi, sin, cos, tan, atan2, hypot
from operator import attrgetter

from PIL import Image
from PIL.ImageDraw import ImageDraw
from shapely.geometry import Polygon, LineString, Point as _Point

def draw_edge(edge, img, drawn):
    """ Draw an edge to an image, if it hasn't been drawn already.
    """
    if edge in drawn:
        return
    
    draw = ImageDraw(img)
    draw.line([(edge.p1.x, edge.p1.y), (edge.p2.x, edge.p2.y)], fill=(0xCC, 0xCC, 0xCC), width=2)
    
    drawn.add(edge)

def draw_collision(collision, img, drawn, reach):
    """ Draw a collision and its rays to an image, if it hasn't been drawn already.
    """
    if collision in drawn:
        return

    draw_edge(collision.edge, img, drawn)
    draw_ray(collision.p_ray, img, drawn, reach)
    draw_ray(collision.n_ray, img, drawn, reach)
    
    if collision.point is None:
        return
    
    p = collision.point
    
    draw = ImageDraw(img)
    draw.line([(p.x - 2, p.y - 2), (p.x + 2, p.y + 2)], fill=(0x99, 0x99, 0x99), width=1)
    draw.line([(p.x - 2, p.y + 2), (p.x + 2, p.y - 2)], fill=(0x99, 0x99, 0x99), width=1)
    
    drawn.add(collision)

def draw_split(split, img, drawn, reach):
    """ Draw a split and its ray to an image, if it hasn't been drawn already.
    """
    if split in drawn:
        return
    
    draw_edge(split.edge, img, drawn)
    draw_ray(split.ray, img, drawn, reach)
    
    p = split.point
    
    draw = ImageDraw(img)
    draw.rectangle([(p.x - 2, p.y - 2), (p.x + 2, p.y + 2)], fill=(0x66, 0x66, 0x66))
    
    drawn.add(split)

def draw_event(event, img, drawn, reach):
    """
    """
    if event.__class__ is CollisionEvent:
        return draw_collision(event, img, drawn, reach)

    elif event.__class__ is SplitEvent:
        return draw_split(event, img, drawn, reach)

def draw_ray(ray, img, drawn, reach):
    """ Draw a ray and its tails to an image, if it hasn't been drawn already.
    """
    if ray in drawn:
        return
    
    for tail in (ray.p_tail, ray.n_tail):
        draw_tail(tail, img, drawn, reach)
    
    p1 = ray.start
    p2 = Point(p1.x + 10 * cos(ray.theta), p1.y + 10 * sin(ray.theta))
    
    color = ray.reflex and (0x00, 0x00, 0x00) or (0xFF, 0x33, 0x00)
    
    draw = ImageDraw(img)
    draw.rectangle([(p1.x - 1, p1.y - 1), (p1.x + 1, p1.y + 1)], fill=color)
    draw.line([(p1.x, p1.y), (p2.x, p2.y)], fill=color, width=1)
    
    drawn.add(ray)

def draw_peak(peak, img, drawn, reach):
    """ Draw a peak's tails to an image, if it hasn't been drawn already.
    """
    if peak in drawn:
        return
    
    for tail in peak.tails:
        draw_tail(tail, img, drawn, reach)
    
    drawn.add(peak)

def draw_tail(tail, img, drawn, reach):
    """ Draw a tail and its tree of edges to an image, if it hasn't been drawn already.
    """
    if tail in drawn:
        return
    
    #for edge in (tail.p_edge, tail.n_edge):
    #    draw_edge(edge, img, drawn)
    
    for other in tail.tails:
        draw_tail(other, img, drawn, reach)
    
    p1 = tail.start
    p2 = tail.end
    
    color = (tail.reach(reach) > reach) and (0x00, 0x66, 0xFF) or (0x66, 0xFF, 0xFF)
    
    draw = ImageDraw(img)
    draw.line([(p1.x, p1.y), (p2.x, p2.y)], fill=color, width=1)
    
    drawn.add(tail)

class Point:
    """ Simple (x, y) point.
    
        Also includes optional is_split boolean flag, used to mark split points.
    """
    def __init__(self, x, y, is_split=False):
        self.x = x
        self.y = y
        self.is_split = is_split

    def __repr__(self):
        return 'Point ' + ('%x (%.1f, %.1f)' % (id(self), self.x, self.y))[2:]

    def left_of(self, point, theta):
        """ Return true if this point is to the left of a line.
        
            Line is defined as a point and direction.
        """
        # location of self relative to the (0, 0) of the given line.
        dx, dy = self.x - point.x, self.y - point.y
        
        # y-position of self after rotation of the line back to theta 0.
        # see http://en.wikipedia.org/wiki/Rotation_matrix
        y = dx * sin(-theta) + dy * cos(-theta)
        
        # points to the left rotate to negative y.
        # remember that in our internal coordinate space y points down as in PIL.
        #
        #            * left
        #
        # point ------------------> theta
        #
        #            right *
        #
        return y < 0

class Edge:
    """ Edge between two points.
    
        Includes points (p1, p2), original containing polygon (poly), and
        previous and next ray pointers (p_ray, n_ray) initialized to None.
    """
    def __init__(self, p1, p2, poly):
        self.p1 = p1
        self.p2 = p2
        self.poly = poly
        
        self.theta = atan2(p2.y - p1.y, p2.x - p1.x)
        
        self.p_ray, self.n_ray = None, None

    def __repr__(self):
        return 'Edge ' + ('%x (%.1f, %.1f, %.1f, %.1f)' % (id(self), self.p1.x, self.p1.y, self.p2.x, self.p2.y))[2:]

class Tail:
    """ A backwards-pointing length of traversed skeleton.
    
        Includes pointers to previous and next edges (p_edge, n_edge), a list
        of preceding tails (tails), knows its own length (length), and has
        start and end points (start, end).
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
        return 'Tail ' + ('%x (%.1f)' % (id(self), self.length))[2:]

    def reach(self, min_reach):
        reach = self.length + max([tail.reach(min_reach) for tail in self.tails])
        boost = self.start.is_split and min_reach or 0
        
        return reach + boost

class Stub:
    """ A tail that has no preceding tails, used to start from the edges.
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

    def reach(self, min_reach):
        return 0

class Ray:
    """ A ray is a forward-pointing length of potential skeleton.
    
        Includes pointers to previous and next tails (p_tail, n_tail),
        a starting point (start), reflex flag and direction (theta).
    """
    def __init__(self, start, p_tail, n_tail):
        self.start = start
        self.p_tail = p_tail
        self.n_tail = n_tail
        self.theta, self.reflex = self._theta_reflex()
        
        self.p_tail.p_edge.n_ray = self
        self.n_tail.n_edge.p_ray = self
        
    def __repr__(self):
        return 'Ray ' + ('%x' % id(self))[2:]

    def _theta_reflex(self):
        n_theta = self.n_tail.n_edge.theta
        p_theta = self.p_tail.p_edge.theta
    
        if abs(tan(n_theta) - tan(p_theta)) < 0.000001:
            # we have parallel edges
            return n_theta, False

        if n_theta < p_theta:
            n_theta += pi * 2

        rotation = n_theta - p_theta
        reflex = False
        
        if rotation > pi:
            if self.p_tail.p_edge.p2 is self.n_tail.n_edge.p1:
                reflex = True
                rotation -= pi * 2
        
        return p_theta + rotation/2 + pi/2, reflex

class CollisionEvent:
    """ A collision is where two rays might potentially meet.
    
        Includes pointers to previous and next rays (p_ray, n_ray),
        point of impact (point), active edge (edge), distance from one
        of the participating edges to use for priority listing, and
        flag for whether this collision closes a peak (is_closure).
    """
    def __init__(self, p_ray, n_ray):
        self.p_ray = p_ray
        self.n_ray = n_ray
        
        assert p_ray.n_tail.n_edge is n_ray.p_tail.p_edge
        self.edge = p_ray.n_tail.n_edge
        
        self.distance, self.point, self.is_closure = self._intersection()

    def __repr__(self):
        return 'Collision Event ' + ('%x' % id(self))[2:]

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
        
            return 0, ray.start, True
        
        invalid = 6378137, None, False
        
        try:
            x, y = line_intersection(ray1.start, ray1.theta, ray2.start, ray2.theta)

            p1, p2 = ray1.p_tail.p_edge.p1, ray1.p_tail.p_edge.p2
            d = point_line_distance(x, y, p1.x, p1.y, p2.x, p2.y)

        except ZeroDivisionError:
            # unsolved intersection
            return invalid
    
        if not _Point(x, y).within(ray1.p_tail.p_edge.poly):
            # collision outside the original polygon
            return invalid
        
        return d, Point(x, y), False

class SplitEvent:
    """ A split is where a ray and an edge potentially split the underlying polygon.
    
        ...
    """
    def __init__(self, ray, edge):
        self.ray = ray
        self.edge = edge
        
        self.distance, self.point, self.is_valid = self._intersection()

    def __repr__(self):
        return 'Split Event ' + ('%x' % id(self))[2:]

    def _intersection(self):
        """
        """
        ray_edges = self.ray.p_tail.p_edge, self.ray.n_tail.n_edge
        distances_points, invalid = [], (6378137, None, False)

        if self.edge in ray_edges:
            return invalid
        
        try:
            # intersection with colliding edge
            xy = line_intersection(self.ray.start, ray_edges[0].theta, self.edge.p1, self.edge.theta)
            edge_xsect = Point(*xy)

            # theta back to the start point
            theta1 = atan2(self.ray.start.y - edge_xsect.y, self.ray.start.x - edge_xsect.x)

            # theta to the intersection with colliding edge
            x, y = line_intersection(self.ray.start, self.ray.theta, self.edge.p1, self.edge.theta)
            theta2 = atan2(y - edge_xsect.y, x - edge_xsect.x)

            # theta between the two
            dx1, dy1 = cos(theta1), sin(theta1)
            dx2, dy2 = cos(theta2), sin(theta2)
            theta = atan2((dy1 + dy2) / 2, (dx1 + dx2) / 2)
            
            # point of potential split event
            x, y = line_intersection(self.ray.start, self.ray.theta, edge_xsect, theta)
            split_point = Point(x, y, True)
            
            if not _Point(x, y).within(self.edge.poly):
                # split point is outside the origin polygon
                return invalid
            
            if split_point.left_of(self.edge.p1, self.edge.theta):
                # split point is to the left of the collision edge
                return invalid

            if split_point.left_of(self.edge.p_ray.start, self.edge.p_ray.theta - pi):
                # split point is to the left of the previous edge ray
                return invalid

            if split_point.left_of(self.edge.n_ray.start, self.edge.n_ray.theta):
                # split point is to the left of the next edge ray
                return invalid
                
        except ZeroDivisionError:
            return invalid

        else:
            x, y = split_point.x, split_point.y
            x1, y1 = self.edge.p1.x, self.edge.p1.y
            x2, y2 = self.edge.p2.x, self.edge.p2.y
        
            d = point_line_distance(x, y, x1, y1, x2, y2)
            
            distances_points.append((d, split_point, True))
        
        if not distances_points:
            return invalid
        
        return sorted(distances_points)[0]

class PeakEvent:
    """
    """
    def __init__(self, *tails):
        ends = set([tail.end for tail in tails])
        assert len(ends) == 1, 'All the adjoined tails must share a common end'

        self.tails = tails

def line_intersection(point1, theta1, point2, theta2):
    """ (x, y) intersection of line (point1, theta1) and (point2, theta2).
        
        Based on parametric form, where:
        x = x1 + cos1 * t
        y = y1 + sin1 * t
        x = x2 + cos2 * t
        y = y2 + sin2 * t
    """
    x1, y1 = point1.x, point1.y
    x2, y2 = point2.x, point2.y
    
    sin1, cos1 = sin(theta1), cos(theta1)
    sin2, cos2 = sin(theta2), cos(theta2)
    
    x = (cos2*sin1*x1 - cos2*cos1*y1 - cos1*sin2*x2 + cos1*cos2*y2) / (cos2*sin1 - cos1*sin2)
    
    if abs(cos1) > 0.0000001:
        y = (sin1*x - sin1*x1 + cos1*y1) / cos1
    else:
        y = (sin2*x - sin2*x2 + cos2*y2) / cos2
    
    return (x, y)

def point_line_distance(x, y, x1, y1, x2, y2):
    """ Distance of point (x, y) from line (x1, y1, x2, y2).
    """
    # see formula 14, http://mathworld.wolfram.com/Point-LineDistance2-Dimensional.html
    return abs((x2 - x1) * (y1 - y) - (x1 - x) * (y2 - y1)) / hypot(x2 - x1, y2 - y1)

def polygon_edges(poly):
    """ Build a list of edges from the exterior ring of a polygon.
    
        Enforces the simplicity and validity of the polygon,
        also ensures that edges are ordered clockwise.
    """
    assert poly.__class__ is Polygon, 'Polygon, not MultiPolygon'
    assert len(poly.interiors) == 0, 'No donut holes, either'
    assert poly.is_valid, 'Seriously amirite?'
    
    points, edges = [], []
    
    for i in range(len(poly.exterior.coords) - 1):
        p = Point(*poly.exterior.coords[i])
        points.append(p)
    
    for (i, p1) in enumerate(points):
        j = (i + 1) % len(points)
        p2 = points[j]
        edge = Edge(p1, p2, poly)
        edges.append(edge)
    
    spin = 0
    
    for (i, edge1) in enumerate(edges):
        j = (i + 1) % len(edges)
        edge2 = edges[j]
        
        theta = edge2.theta - edge1.theta
        
        if theta > pi:
            theta -= pi * 2
        elif theta < -pi:
            theta += pi * 2
        
        spin += theta
    
    if abs(spin + pi*2) < 0.000001:
        # uh oh, counterclockwise polygon.
        edges = [Edge(e.p2, e.p1, poly) for e in reversed(edges)]
    
    return edges

def edge_rays(edges):
    """ Build a list of rays pointing inward from junctions between edges.
    """
    stubs, rays = [], []
    
    for (i, edge) in enumerate(edges):
        j = (i + 1) % len(edges)
        stub = Stub(edge.p2, edges[i], edges[j])
        stubs.append(stub)

    for stub in stubs:
        ray = Ray(stub.end, stub, stub)
        rays.append(ray)

    edges = set()
    
    return rays

def ray_events(rays):
    """ Build a sorted list of events between pairs of rays.
    """
    events = []
    
    for (i, ray1) in enumerate(rays):
        j = (i + 1) % len(rays)
        ray2 = rays[j]
        collision = CollisionEvent(ray1, ray2)
        events.append(collision)
    
    events.sort(key=attrgetter('distance'))
    
    for ray in rays:
        if ray.reflex:
            ray_splits = []
        
            for collision in events:
                if collision.__class__ is not CollisionEvent:
                    continue
                
                split = SplitEvent(ray, collision.edge)
                
                if split.is_valid:
                    ray_splits.append(split)
            
            if ray_splits:
                ray_splits.sort(key=attrgetter('distance'))
                split = ray_splits[0]
                events.append(split)
                
                # for (i, collision) in enumerate(events):
                #     if split.distance < collision.distance:
                #         events.insert(i, split)
                #         break
    
    events.sort(key=attrgetter('distance'))
    
    print ', '.join(['%s at %.3f' % (e, e.distance) for e in events])
    
    return events

def insert_event(new_event, events):
    """ Insert a new event into an ordered list of events in the right spot.
    """
    for (index, event) in enumerate(events):
        if new_event.distance < event.distance:
            break

    events.insert(index, new_event)

if __name__ == '__main__':
    
    # y-intersection
    poly1 = LineString(((50, 50), (150, 150), (250, 150))).buffer(40, 2)
    poly2 = LineString(((60, 240), (150, 150))).buffer(50, 2)
    poly = poly1.union(poly2)
    
    # doubled-up lines
    poly1 = LineString(((50, 110), (220, 160))).buffer(40, 2)
    poly2 = LineString(((80, 140), (250, 190))).buffer(40, 2)
    poly = poly1.union(poly2)
    
    poly = Polygon(((150, 25), (250, 250), (50, 250))) # simple triangle
    poly = Polygon(((140, 25), (160, 25), (250, 100), (250, 250), (50, 250), (40, 240))) # lumpy triangle
    poly = Polygon(((75, 75), (220, 70), (230, 80), (230, 220), (220, 230), (140, 170), (75, 225))) # reflex point
    poly = LineString(((50, 50), (200, 50), (250, 100), (250, 250), (50, 250))).buffer(30, 2) # c-curve street

    edges = polygon_edges(poly)
    rays = edge_rays(edges)
    events = ray_events(rays)
    peaks = []
    
    print len(edges), 'edges,', len(rays), 'rays,', len(events), 'events.'
    
    frame = 1
    
    img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
    drawn = set()
    
    for event in events:
        draw_event(event, img, drawn, 70)
    
    img.save('skeleton-%03d.png' % frame)

    print frame, '-' * 40
    
    while len(events):
    
        frame += 1
        
        event = events.pop(0)
        
        if event.__class__ is SplitEvent:
            split = event
            
            nu_tail = Tail(split.point, split.ray.p_tail.p_edge, split.ray.n_tail.n_edge, split.ray.p_tail, split.ray.n_tail)
            nu_stub = Stub(split.point, split.edge, split.edge)
            
            nu_ray1 = Ray(split.point, nu_tail, nu_stub)
            nu_ray2 = Ray(split.point, nu_stub, nu_tail)
            
            for old_collision in events[:]:
                if old_collision.__class__ is not CollisionEvent:
                    continue
                
                if old_collision.n_ray is split.ray:
                    new_collision = CollisionEvent(old_collision.p_ray, nu_ray1)
                    insert_event(new_collision, events)
                    events.remove(old_collision)
            
            for old_collision in events:
                if old_collision.__class__ is not CollisionEvent:
                    continue
                
                if old_collision.p_ray is split.ray:
                    new_collision = CollisionEvent(nu_ray2, old_collision.n_ray)
                    insert_event(new_collision, events)
                    events.remove(old_collision)
            
            for old_collision in events[:]:
                if old_collision.__class__ is not CollisionEvent:
                    continue
                
                if old_collision.edge is split.edge:
                    new_collision = CollisionEvent(nu_ray1, old_collision.n_ray)
                    insert_event(new_collision, events)

                    new_collision = CollisionEvent(old_collision.p_ray, nu_ray2)
                    insert_event(new_collision, events)

                    events.remove(old_collision)
        
        elif event.__class__ is CollisionEvent:
            collision = event
        
            if collision.is_closure and collision.n_ray is collision.p_ray:
                tails = set([collision.n_ray.n_tail, collision.n_ray.p_tail])
                peak = PeakEvent(*tails)
                peaks.append(peak)
            
            else:
                p_ray = collision.p_ray
                n_ray = collision.n_ray
                point = collision.point
                
                p_tail = Tail(point, p_ray.p_tail.p_edge, p_ray.n_tail.n_edge, p_ray.p_tail, p_ray.n_tail)
                n_tail = Tail(point, n_ray.p_tail.p_edge, n_ray.n_tail.n_edge, n_ray.p_tail, n_ray.n_tail)
                new_ray = Ray(point, p_tail, n_tail)
                
                for old_split in events[:]:
                    if old_split.__class__ is not SplitEvent:
                        continue
                    
                    if old_split.ray in (p_ray, n_ray):
                        events.remove(old_split)
                
                for old_collision in events[:]:
                    if old_collision.__class__ is not CollisionEvent:
                        continue
                
                    if old_collision.n_ray is p_ray:
                        new_collision = CollisionEvent(old_collision.p_ray, new_ray)
                        insert_event(new_collision, events)
                        events.remove(old_collision)
                    
                for old_collision in events[:]:
                    if old_collision.__class__ is not CollisionEvent:
                        continue
                
                    if old_collision.p_ray is n_ray:
                        new_collision = CollisionEvent(new_ray, old_collision.n_ray)
                        insert_event(new_collision, events)
                        events.remove(old_collision)
        
        img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
        drawn = set()
        
        for event in events:
            draw_event(event, img, drawn, 70)
        
        for peak in peaks:
            draw_peak(peak, img, drawn, 70)
        
        img.save('skeleton-%03d.png' % frame)
    
        print frame, '-' * 40

    print len(peaks), 'peaks.'
