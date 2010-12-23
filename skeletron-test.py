from PIL import Image
from PIL.ImageDraw import ImageDraw
from shapely.wkt import dumps as wkt_dumps, loads as wkt_loads
from shapely.geometry import Polygon, LineString

from Skeletron import generate_states, polygon_spine
from Skeletron.draw import draw_event, draw_peak

def get_xform(poly):
    """
    """
    xmin, ymin, xmax, ymax = poly.bounds
    
    xm = 280 / (xmax - xmin)
    ym = 280 / (ymax - ymin)
    
    m = min(xm, ym)
    xb = 150 - m * (xmax + xmin) / 2
    yb = 150 - m * (ymax + ymin) / 2
    
    xform = lambda x, y: (m * x + xb, m * y + yb)
    
    return xform

if __name__ == '__main__':
    
    # doubled-up lines
    poly1 = LineString(((50, 110), (220, 160))).buffer(40, 2)
    poly2 = LineString(((80, 140), (250, 190))).buffer(40, 2)
    poly = poly1.union(poly2)
    
    # y-intersection
    poly1 = LineString(((50, 50), (150, 150), (250, 150))).buffer(40, 2)
    poly2 = LineString(((60, 240), (150, 150))).buffer(50, 2)
    poly = poly1.union(poly2)
    
    # Tandang Sora Street
    poly = wkt_loads('POLYGON ((-13625496.4396574757993221 4548638.8825872316956520, -13625496.4395814724266529 4548638.8825104515999556, -13625472.9695814736187458 4548615.1725104516372085, -13625468.6301940716803074 4548604.5436974689364433, -13625473.0774895492941141 4548593.9595814729109406, -13625483.7063025329262018 4548589.6201940709725022, -13625494.2904185280203819 4548594.0674895485863090, -13625517.7603750806301832 4548617.7774456581100821, -13625546.1603425238281488 4548646.4674127679318190, -13625550.4998064786195755 4548657.0961944973096251, -13625546.0525872316211462 4548667.6803425233811140, -13625535.4238055031746626 4548672.0198064781725407, -13625524.8396574761718512 4548667.5725872311741114, -13625496.4396574757993221 4548638.8825872316956520))')
    
    poly = Polygon(((150, 25), (250, 250), (50, 250))) # simple triangle
    poly = Polygon(((140, 25), (160, 25), (250, 100), (250, 250), (50, 250), (40, 240))) # lumpy triangle
    poly = Polygon(((75, 75), (220, 70), (230, 80), (230, 220), (220, 230), (140, 170), (75, 225))) # reflex point
    poly = LineString(((50, 50), (200, 50), (250, 100), (250, 250), (50, 250))).buffer(30, 2) # c-curve street
    poly = LineString(((50, 50), (200, 50), (250, 100), (250, 250), (50, 250), (60, 60))).buffer(30, 2) # o-curve street
    
    xform = get_xform(poly)

    print 'Input', '-' * 40
    print wkt_dumps(poly)
    
    frame = 1
    
    for (events, peaks) in generate_states(poly):
    
        img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
        drawn = set()
        
        for event in events:
            draw_event(event, img, drawn, 60, xform)
        
        for peak in peaks:
            draw_peak(peak, img, drawn, 60, xform)
        
        img.save('skeleton-%03d.png' % frame)
    
        print frame
        
        frame += 1

    print len(peaks), 'peaks.'
    
    spine = polygon_spine(poly, 70)
    
    print 'Output', '-' * 40
    print wkt_dumps(spine)

    img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
    draw = ImageDraw(img)
    
    polys = hasattr(poly, 'geoms') and poly.geoms or [poly]
    
    for poly in polys:
        draw.polygon(list(poly.exterior.coords), outline=(0x99, 0x99, 0x99))
        
        for ring in poly.interiors:
            draw.polygon(list(ring.coords), outline=(0x99, 0x99, 0x99))

    geoms = hasattr(spine, 'geoms') and spine.geoms or [spine]
    
    for geom in geoms:
        draw.line(list(geom.coords), fill=(0x00, 0x00, 0x00))
    
    img.save('skeleton-fin.png')
