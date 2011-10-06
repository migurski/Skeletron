from voronoi import computeVoronoiDiagram
from shapely.ops import cascaded_union, linemerge
from shapely.geometry import LineString, asShape

def skeletron(geoms):
    buffer = cascaded_union(geoms).buffer(0)
    if shell.geom_type == "Polygon":
        shells = [buffer]
    else:
        shells = buffer.geoms
    spines = []
    for shell in shells:
        coords = list(shell.exterior.coords)
        vertices, _, edges = computeVoronoiDiagram(coords)
        linework = []
        for _, v1, v2 in edges:
            if v1 == -1 or v2 == -1: continue # half-infinite
            pt1, pt2 = vertices[v1], vertices[v2]
            segment = LineString(((pt1.x, pt1.x), (pt2.x, pt2.y)))
            if not segment.intersects(shell):
                linework.append(segment)
        spines.append(linemerge(linework))
    return spines

if __name__ == "__main__":
    import json, sys
    collection = json.load(sys.stdin)
    for feature in collection["features"]:
        geom = asShape(feature["geometry"])
        spines = skeletron([geom])
        feature["geometry"] = MultiLineString(spines).__geo_interface__
    json.dump(collection, sys.stdout)
