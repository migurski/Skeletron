from PIL import Image
from PIL.ImageDraw import ImageDraw
from shapely.geometry import Polygon, LineString

from Skeletron import generate_states, polygon_spine
from Skeletron.draw import draw_event, draw_peak

if __name__ == '__main__':
    
    # doubled-up lines
    poly1 = LineString(((50, 110), (220, 160))).buffer(40, 2)
    poly2 = LineString(((80, 140), (250, 190))).buffer(40, 2)
    poly = poly1.union(poly2)
    
    poly = Polygon(((150, 25), (250, 250), (50, 250))) # simple triangle
    poly = Polygon(((140, 25), (160, 25), (250, 100), (250, 250), (50, 250), (40, 240))) # lumpy triangle
    poly = Polygon(((75, 75), (220, 70), (230, 80), (230, 220), (220, 230), (140, 170), (75, 225))) # reflex point
    poly = LineString(((50, 50), (200, 50), (250, 100), (250, 250), (50, 250))).buffer(30, 2) # c-curve street
    
    # y-intersection
    poly1 = LineString(((50, 50), (150, 150), (250, 150))).buffer(40, 2)
    poly2 = LineString(((60, 240), (150, 150))).buffer(50, 2)
    poly = poly1.union(poly2)
    
    frame = 1
    
    for (events, peaks) in generate_states(poly):
    
        img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
        drawn = set()
        
        for event in events:
            draw_event(event, img, drawn, 70)
        
        for peak in peaks:
            draw_peak(peak, img, drawn, 70)
        
        img.save('skeleton-%03d.png' % frame)
    
        print frame
        
        frame += 1

    print len(peaks), 'peaks.'
    
    spine = polygon_spine(poly, 70)

    img = Image.new('RGB', (300, 300), (0xFF, 0xFF, 0xFF))
    draw = ImageDraw(img)
    
    polys = hasattr(poly, 'geoms') and poly.geoms or [poly]
    
    for poly in polys:
        draw.polygon(list(poly.exterior.coords), outline=(0x99, 0x99, 0x99))

    geoms = hasattr(spine, 'geoms') and spine.geoms or [spine]
    
    for geom in geoms:
        draw.line(list(geom.coords), fill=(0x00, 0x00, 0x00))
    
    img.save('skeleton-fin.png')
