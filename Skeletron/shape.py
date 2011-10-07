from voronoi import computeVoronoiDiagram, Site
from shapely.ops import cascaded_union, linemerge
from shapely.geometry import MultiLineString, LineString, shape
from shapely.prepared import prep
from math import ceil, hypot

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


def skeletron(geoms, epsilon=0.00005):
    if len(geoms) > 1:
        geoms = cascaded_union(geoms) #.buffer(0)
    else:
        geoms = geoms[0]
    buffer = geoms.buffer(epsilon)
    if buffer.geom_type == "Polygon":
        shells = [buffer]
    else:
        shells = buffer.geoms
    spines = []
    for shell in shells:
        pshell = prep(shell)
        pshellext = prep(shell.exterior)
        print >>sys.stderr, "densify"
        coords = [Site(x,y) for x, y in densify_line(shell.exterior.coords, epsilon)]
        print >>sys.stderr, "voronoi"
        vertices, _, edges = computeVoronoiDiagram(coords)
        linework = []
        print >>sys.stderr, "segments"
        for _, v1, v2 in edges:
            if v1 == -1 or v2 == -1: continue # half-infinite
            pt1, pt2 = vertices[v1], vertices[v2]
            segment = LineString((pt1, pt2))
            if pshell.contains(segment) and not pshellext.intersects(segment):
                linework.append(segment)
        print >>sys.stderr, "linemerge"
        spines.append(linemerge(linework))
    return spines

if __name__ == "__main__":
    import json, sys
    collection = json.load(sys.stdin)
    for n, feature in enumerate(collection["features"]):
        print >>sys.stderr, n
        geom = shape(feature["geometry"])
        spines = skeletron([geom], 2)
        feature["geometry"] = spines[0].__geo_interface__
    json.dump(collection, sys.stdout)
