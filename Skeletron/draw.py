from math import cos, sin

from PIL.ImageDraw import ImageDraw

def draw_edge(edge, img, drawn, xform):
    """ Draw an edge to an image, if it hasn't been drawn already.
    """
    if edge in drawn:
        return
    
    x1, y1 = (xform is None) and (edge.p1.x, edge.p1.y) or xform(edge.p1.x, edge.p1.y)
    x2, y2 = (xform is None) and (edge.p2.x, edge.p2.y) or xform(edge.p2.x, edge.p2.y)

    draw = ImageDraw(img)
    draw.line([(x1, y1), (x2, y2)], fill=(0xCC, 0xCC, 0xCC), width=2)
    
    drawn.add(edge)

def draw_collision(collision, img, drawn, reach, xform):
    """ Draw a collision and its rays to an image, if it hasn't been drawn already.
    """
    if collision in drawn:
        return

    draw_edge(collision.edge, img, drawn, xform)
    draw_ray(collision.p_ray, img, drawn, reach, xform)
    draw_ray(collision.n_ray, img, drawn, reach, xform)
    
    if collision.point is None:
        return
    
    p = collision.point
    
    x, y = (xform is None) and (p.x, p.y) or xform(p.x, p.y)
    
    draw = ImageDraw(img)
    draw.line([(x - 2, y - 2), (x + 2, y + 2)], fill=(0x99, 0x99, 0x99), width=1)
    draw.line([(x - 2, y + 2), (x + 2, y - 2)], fill=(0x99, 0x99, 0x99), width=1)
    
    drawn.add(collision)

def draw_split(split, img, drawn, reach, xform):
    """ Draw a split and its ray to an image, if it hasn't been drawn already.
    """
    if split in drawn:
        return
    
    draw_edge(split.edge, img, drawn, xform)
    draw_ray(split.ray, img, drawn, reach, xform)
    
    p = split.point

    x, y = (xform is None) and (p.x, p.y) or xform(p.x, p.y)
    
    draw = ImageDraw(img)
    draw.rectangle([(x - 2, y - 2), (x + 2, y + 2)], fill=(0x66, 0x66, 0x66))
    
    drawn.add(split)

def draw_event(event, img, drawn, reach, xform):
    """
    """
    if hasattr(event, 'edge') and hasattr(event, 'ray'):
        # guess it's a split
        return draw_split(event, img, drawn, reach, xform)

    elif hasattr(event, 'n_ray') and hasattr(event, 'p_ray'):
        # guess it's a collision
        return draw_collision(event, img, drawn, reach, xform)

    else:
        # no idea
        raise Exception('?')

def draw_ray(ray, img, drawn, reach, xform):
    """ Draw a ray and its tails to an image, if it hasn't been drawn already.
    """
    if ray in drawn:
        return
    
    for tail in (ray.p_tail, ray.n_tail):
        draw_tail(tail, img, drawn, reach, xform)
    
    p1 = ray.start
    
    x1, y1 = (xform is None) and (p1.x, p1.y) or xform(p1.x, p1.y)
    x2, y2 = x1 + 10 * cos(ray.theta), y1 + 10 * sin(ray.theta)

    color = ray.reflex and (0x00, 0x00, 0x00) or (0xFF, 0x33, 0x00)
    
    draw = ImageDraw(img)
    draw.rectangle([(x1 - 1, y1 - 1), (x1 + 1, y1 + 1)], fill=color)
    draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
    
    drawn.add(ray)

def draw_peak(peak, img, drawn, reach, xform):
    """ Draw a peak's tails to an image, if it hasn't been drawn already.
    """
    if peak in drawn:
        return
    
    for tail in peak.tails:
        draw_tail(tail, img, drawn, reach, xform)
    
    drawn.add(peak)

def draw_tail(tail, img, drawn, reach, xform):
    """ Draw a tail and its tree of edges to an image, if it hasn't been drawn already.
    """
    if tail in drawn:
        return
    
    #for edge in (tail.p_edge, tail.n_edge):
    #    draw_edge(edge, img, drawn, xform)
    
    for other in tail.tails:
        draw_tail(other, img, drawn, reach, xform)
    
    p1 = tail.start
    p2 = tail.end

    x1, y1 = (xform is None) and (p1.x, p1.y) or xform(p1.x, p1.y)
    x2, y2 = (xform is None) and (p2.x, p2.y) or xform(p2.x, p2.y)
    
    color = (tail.reach(reach) > reach) and (0x00, 0x66, 0xFF) or (0x66, 0xFF, 0xFF)
    
    draw = ImageDraw(img)
    draw.line([(x1, y1), (x2, y2)], fill=color, width=1)
    
    drawn.add(tail)
