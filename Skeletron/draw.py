from math import cos, sin

from PIL.ImageDraw import ImageDraw

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
    if hasattr(event, 'edge') and hasattr(event, 'ray'):
        # guess it's a split
        return draw_split(event, img, drawn, reach)

    elif hasattr(event, 'n_ray') and hasattr(event, 'p_ray'):
        # guess it's a collision
        return draw_collision(event, img, drawn, reach)

    else:
        # no idea
        raise Exception('?')

def draw_ray(ray, img, drawn, reach):
    """ Draw a ray and its tails to an image, if it hasn't been drawn already.
    """
    if ray in drawn:
        return
    
    for tail in (ray.p_tail, ray.n_tail):
        draw_tail(tail, img, drawn, reach)
    
    p1 = ray.start
    x2, y2 = p1.x + 10 * cos(ray.theta), p1.y + 10 * sin(ray.theta)
    
    color = ray.reflex and (0x00, 0x00, 0x00) or (0xFF, 0x33, 0x00)
    
    draw = ImageDraw(img)
    draw.rectangle([(p1.x - 1, p1.y - 1), (p1.x + 1, p1.y + 1)], fill=color)
    draw.line([(p1.x, p1.y), (x2, y2)], fill=color, width=1)
    
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
