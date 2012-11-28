from sys import stdin, stdout
from math import hypot, ceil, sqrt
from os.path import splitext
from gzip import GzipFile
from bz2 import BZ2File

from shapely.geometry import Polygon
from shapely.ops import cascaded_union

def simplify_line_vw(points, small_area=100):
    """ Simplify a line of points using V-W down to the given area.
    """
    while len(points) > 3:
        
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
    
    return list(points)

def simplify_line_dp(pts, tolerance):
    """ Pure-Python Douglas-Peucker line simplification/generalization
        
        this code was written by Schuyler Erle <schuyler@nocat.net> and is
          made available in the public domain.
        
        the code was ported from a freely-licensed example at
          http://www.3dsoftware.com/Cartography/Programming/PolyLineReduction/
        
        the original page is no longer available, but is mirrored at
          http://www.mappinghacks.com/code/PolyLineReduction/
    """
    anchor  = 0
    floater = len(pts) - 1
    stack   = []
    keep    = set()

    stack.append((anchor, floater))  
    while stack:
        anchor, floater = stack.pop()
      
        # initialize line segment
        if pts[floater] != pts[anchor]:
            anchorX = float(pts[floater][0] - pts[anchor][0])
            anchorY = float(pts[floater][1] - pts[anchor][1])
            seg_len = sqrt(anchorX ** 2 + anchorY ** 2)
            # get the unit vector
            anchorX /= seg_len
            anchorY /= seg_len
        else:
            anchorX = anchorY = seg_len = 0.0
    
        # inner loop:
        max_dist = 0.0
        farthest = anchor + 1
        for i in range(anchor + 1, floater):
            dist_to_seg = 0.0
            # compare to anchor
            vecX = float(pts[i][0] - pts[anchor][0])
            vecY = float(pts[i][1] - pts[anchor][1])
            seg_len = sqrt( vecX ** 2 + vecY ** 2 )
            # dot product:
            proj = vecX * anchorX + vecY * anchorY
            if proj < 0.0:
                dist_to_seg = seg_len
            else: 
                # compare to floater
                vecX = float(pts[i][0] - pts[floater][0])
                vecY = float(pts[i][1] - pts[floater][1])
                seg_len = sqrt( vecX ** 2 + vecY ** 2 )
                # dot product:
                proj = vecX * (-anchorX) + vecY * (-anchorY)
                if proj < 0.0:
                    dist_to_seg = seg_len
                else:  # calculate perpendicular distance to line (pythagorean theorem):
                    dist_to_seg = sqrt(abs(seg_len ** 2 - proj ** 2))
                if max_dist < dist_to_seg:
                    max_dist = dist_to_seg
                    farthest = i

        if max_dist <= tolerance: # use line segment
            keep.add(anchor)
            keep.add(floater)
        else:
            stack.append((anchor, farthest))
            stack.append((farthest, floater))

    keep = list(keep)
    keep.sort()
    return [pts[i] for i in keep]

def densify_line(points, distance):
    """ Densify a line of points using the given distance.
    """
    coords = [points[0]]
    
    for curr_coord in list(points)[1:]:
        prev_coord = coords[-1]
    
        dx, dy = curr_coord[0] - prev_coord[0], curr_coord[1] - prev_coord[1]
        steps = ceil(hypot(dx, dy) / distance)
        count = int(steps)
        
        while count:
            prev_coord = prev_coord[0] + dx/steps, prev_coord[1] + dy/steps
            coords.append(prev_coord)
            count -= 1
    
    return coords

def polygon_rings(polygon):
    """ Given a buffer polygon, return a series of point rings.
    
        Return a list of interiors and exteriors all together.
    """
    if polygon.type == 'Polygon':
        return [polygon.exterior] + list(polygon.interiors)
    
    rings = []
    
    for geom in polygon.geoms:
        rings.append(geom.exterior)
        rings.extend(list(geom.interiors))
    
    return rings

def open_file(name, mode='r'):
    """
    """
    if name == '-' and mode == 'r':
        return stdin

    if name == '-' and mode == 'w':
        return stdout
    
    base, ext = splitext(name)
    
    if ext == '.bz2':
        return BZ2File(name, mode)

    if ext == '.gz':
        return GzipFile(name, mode)

    return open(name, mode)
