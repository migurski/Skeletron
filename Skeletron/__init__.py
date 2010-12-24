from math import pi, sin, cos, tan, atan2, hypot
from itertools import combinations
from operator import attrgetter

from shapely.geometry import Polygon, LineString, Point as _Point
from shapely.geometry.base import geom_factory
from shapely.geos import lgeos

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
        return y <= 0.0000001

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
    
    def as_lines(self, min_reach):
        """
        """
        if not self.reach(min_reach):
            return []
        
        lines = [LineString(((self.start.x, self.start.y), (self.end.x, self.end.y)))]
        
        for tail in self.tails:
            if tail.reach(min_reach) > min_reach:
                lines += tail.as_lines(min_reach)
        
        return lines

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
        
        # n_theta += pi/2
        # p_theta += pi/2
        # 
        # nx, ny = cos(n_theta), sin(n_theta)
        # px, py = cos(p_theta), sin(p_theta)
        # 
        # theta = atan2((ny + py) / 2, (nx + px) / 2)
        # return theta, reflex
        
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
        return 'Collision Event ' + ('%x @%.2f' % (id(self), self.distance))[2:]

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
            p3, p4 = ray2.n_tail.n_edge.p1, ray2.n_tail.n_edge.p2

            d1 = point_line_distance(x, y, p1.x, p1.y, p2.x, p2.y)
            d2 = point_line_distance(x, y, p3.x, p3.y, p4.x, p4.y)
            
            d = min(d1, d2)

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
        return 'Split Event ' + ('%x @%.2f' % (id(self), self.distance))[2:]

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

    def as_lines(self, min_reach):
        """
        """
        lines = []
        
        for tail in self.tails:
            if tail.reach(min_reach) > min_reach:
                lines += tail.as_lines(min_reach)
        
        return lines

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

def _polygon_edges(poly, clockwise=True):
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
    
    to_skip = set()
    
    for (i, p1) in enumerate(points):
        j = (i + 1) % len(points)
        k = (i + 2) % len(points)
        p2, p3 = points[j], points[k]
        
        t1 = atan2(p2.y - p1.y, p2.x - p1.x)
        t2 = atan2(p3.y - p2.y, p3.x - p2.x)
        
        if abs(t1 - t2) < 0.001:
            # p2 seems to not have much of an angle to it - skip it
            to_skip.add(p2)
    
    for skipped in to_skip:
        points.remove(skipped)
    
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
    
    want_direction = clockwise and 'cw' or 'ccw'
    got_direction = (abs(spin + pi*2) < 0.000001) and 'ccw' or 'cw'
    
    if want_direction != got_direction:
        # uh oh, opposite polygon.
        edges = [Edge(e.p2, e.p1, poly) for e in reversed(edges)]
    
    return edges

def _edge_rays(edges):
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

    return rays

def _ray_events(rays):
    """ Build a sorted list of events between pairs of rays.
    """
    events = []
    
    for (ray1, ray2) in combinations(rays, 2):
        if ray1.n_tail.n_edge is ray2.p_tail.p_edge:
            collision = CollisionEvent(ray1, ray2)
            events.append(collision)
        elif ray2.n_tail.n_edge is ray1.p_tail.p_edge:
            collision = CollisionEvent(ray2, ray1)
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
    
    return events

def polygon_events(poly):
    """ Build a sorted list of events for a polygon.
    """
    assert poly.__class__ is Polygon, 'Polygon, not MultiPolygon'
    assert poly.is_valid, 'Seriously amirite?'
    
    rays, rings = [], [poly.exterior] + list(poly.interiors)
    
    for (i, ring) in enumerate(rings):
        clockwise = (i == 0)
        edges = _polygon_edges(Polygon(list(ring.coords)), clockwise)
        edges = [Edge(e.p1, e.p2, poly) for e in edges]
        rays += _edge_rays(edges)
    
    return _ray_events(rays)

def insert_event(new_event, events):
    """ Insert a new event into an ordered list of events in the right spot.
    """
    for (index, event) in enumerate(events):
        if new_event.distance < (event.distance - 0.000001):
            break

    events.insert(index, new_event)

def handle_split(split, events):
    """
    """
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
    
    for old_collision in events[:]:
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

def handle_collision(collision, events):
    """
    """
    if collision.is_closure and collision.n_ray is collision.p_ray:
        tails = set([collision.n_ray.n_tail, collision.n_ray.p_tail])
        peak = PeakEvent(*tails)
        return peak
    
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
        
        elif old_split.edge in (n_ray.p_tail.p_edge, p_ray.n_tail.n_edge):
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

def generate_states(poly):
    """
    """
    events, peaks = polygon_events(poly), []
    
    yield events, peaks

    while len(events):
        event = events.pop(0)
        
        if event.__class__ is SplitEvent:
            handle_split(event, events)
        
        elif event.__class__ is CollisionEvent:
            peak = handle_collision(event, events)
            
            if peak:
                peaks.append(peak)
        
        yield events, peaks

def get_peaks(poly):
    """
    """
    for (events, peaks) in generate_states(poly):
        pass

    return peaks

def polygon_spine(poly, fringe):
    """
    """
    lines = []
    
    for peak in get_peaks(poly):
        lines += peak.as_lines(fringe)
    
    shape = reduce(lambda a, b: a.union(b), lines)
    result = lgeos.GEOSLineMerge(shape._geom)
    
    return geom_factory(result)
