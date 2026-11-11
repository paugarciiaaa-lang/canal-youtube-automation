#!/usr/bin/env python3
"""More dynamic, colorful whiteboard-animation preview for Caspitas."""
from __future__ import annotations
import argparse
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT, FPS = 1280, 720, 24
SCENE_SECONDS, SCENES = 6, 3
PAPER = (250, 249, 245)
INK = (28, 30, 32)
RED = (218, 67, 55)
BLUE = (52, 116, 170)
YELLOW = (238, 184, 55)
GREEN = (65, 139, 105)
PALETTE = [RED, BLUE, YELLOW, GREEN]

def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def ease(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1-p) ** 3

def phase(t, start, duration=.22):
    return ease((t-start)/duration)

def line(draw, pts, p, color=INK, width=6):
    if p <= 0: return
    total = sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
    remaining = total * min(1,p)
    visible = [pts[0]]
    for a,b in zip(pts,pts[1:]):
        length = math.dist(a,b)
        if remaining <= 0: break
        f = min(1, remaining/length)
        visible.append((int(a[0]+(b[0]-a[0])*f), int(a[1]+(b[1]-a[1])*f)))
        remaining -= length
        if f < 1: break
    if len(visible)>1: draw.line(visible, fill=color, width=width, joint="curve")

def circle(draw, box, p, color=INK, width=6):
    if p>0: draw.arc(box, -90, -90+360*min(1,p), fill=color, width=width)

def text_pop(draw, xy, value, p, size=34, color=INK, bold=True):
    if p<=0: return
    f=font(size,bold)
    draw.text(xy,value,fill=color,font=f)

def marker_arrow(draw, a, b, p, color=RED, width=7):
    line(draw,[a,b],p,color,width)
    if p>.85:
        ang=math.atan2(b[1]-a[1],b[0]-a[0])
        tip=b
        left=(b[0]-22*math.cos(ang-.55),b[1]-22*math.sin(ang-.55))
        right=(b[0]-22*math.cos(ang+.55),b[1]-22*math.sin(ang+.55))
        draw.polygon([tip,left,right],fill=color)

def stickman(draw, x, y, t):
    # Walking/running legs and waving arm animate continuously.
    bob=math.sin(t*math.pi*2)*5
    yy=y+bob
    circle(draw,(x-31,yy-31,x+31,yy+31),phase(t,0),INK,6)
    line(draw,[(x,yy+31),(x,yy+132)],phase(t,.08),INK,8)
    line(draw,[(x,yy+65),(x-58,yy+104)],phase(t,.18),INK,7)
    arm_end=(x+72,yy+40+int(10*math.sin(t*math.pi*2)))
    line(draw,[(x,yy+65),arm_end],phase(t,.28),BLUE,8)
    swing=34*math.sin(t*math.pi*2)
    line(draw,[(x,yy+132),(x-48+swing,yy+205)],phase(t,.38),INK,8)
    line(draw,[(x,yy+132),(x+48-swing,yy+205)],phase(t,.48),INK,8)
    if t>.35:
        draw.ellipse((x-10,yy-5,x-3,yy+2),fill=INK)
        draw.ellipse((x+6,yy-5,x+13,yy+2),fill=INK)
        draw.arc((x-12,yy+2,x+13,yy+22),10,170,fill=RED,width=3)

def scene_one(d,t):
    text_pop(d,(105,55),"UN MISTERIO",phase(t,0,.25),54,INK)
    text_pop(d,(105,116),"QUE NADIE HA PODIDO EXPLICAR",phase(t,.12,.3),30,RED)
    line(d,[(105,165),(780,165)],phase(t,.2),YELLOW,9)
    stickman(d,390,270,t)
    # Floating question marks and clue card
    if t>.2:
        pulse=1+0.12*math.sin(t*math.pi*5)
        f=font(int(78*pulse),True); d.text((525,220),"?",font=f,fill=RED)
        d.text((600,315),"?",font=f,fill=BLUE)
    p=phase(t,.32,.25)
    line(d,[(760,235),(1100,235),(1100,545),(760,545),(760,235)],p,INK,6)
    text_pop(d,(805,270),"ARCHIVO",phase(t,.42),28,BLUE)
    line(d,[(805,330),(1050,330)],phase(t,.5),INK,4)
    line(d,[(805,380),(1025,380)],phase(t,.58),INK,4)
    line(d,[(805,430),(1060,430)],phase(t,.66),INK,4)
    circle(d,(845,455,930,540),phase(t,.72),RED,7)
    text_pop(d,(125,585),"¿QUÉ OCURRIÓ REALMENTE?",phase(t,.78),32,RED)

def scene_two(d,t):
    text_pop(d,(100,55),"SIGUE EL RASTRO",phase(t,0,.2),48,INK)
    # Animated route with pulsing locations
    route=[(130,360),(300,245),(480,330),(665,205),(850,310),(1090,190)]
    for i in range(len(route)-1):
        p=phase(t,.12+i*.1,.18)
        line(d,route[i:i+2],p,BLUE,8)
    for i,(x,y) in enumerate(route):
        p=phase(t,.18+i*.1,.12)
        if p:
            r=int(17+4*math.sin(t*math.pi*6+i))
            d.ellipse((x-r,y-r,x+r,y+r),outline=RED if i%2==0 else YELLOW,width=7)
    # Magnifier moves across the route
    mx=220+760*min(1,t/.95)
    my=470-100*math.sin(t*math.pi*2)
    circle(d,(mx-55,my-55,mx+55,my+55),1,INK,8)
    line(d,[(mx+40,my+40),(mx+112,my+112)],1,INK,13)
    text_pop(d,(380,535),"UNA PISTA CAMBIA TODO",phase(t,.58),34,RED)
    marker_arrow(d,(930,520),(1080,420),phase(t,.72),GREEN,7)

def scene_three(d,t):
    text_pop(d,(95,48),"LAS PIEZAS ENCAJAN",phase(t,0,.2),48,INK)
    cards=[(90,210,390,430),(490,210,790,430),(890,210,1190,430)]
    labels=["FECHAS","TESTIMONIOS","PRUEBAS"]
    colors=[RED,BLUE,GREEN]
    for i,((x1,y1,x2,y2),label,c) in enumerate(zip(cards,labels,colors)):
        p=phase(t,.12+i*.16,.22)
        line(d,[(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)],p,INK,6)
        text_pop(d,(x1+22,y1+28),label,phase(t,.22+i*.16),25,c)
        for j in range(3):
            line(d,[(x1+24,y1+92+j*34),(x2-25-(j*24),y1+92+j*34)],phase(t,.3+i*.16+j*.06),INK,4)
        if p>.7:
            circle(d,(x2-62,y1+12,x2-22,y1+52),phase(t,.5+i*.1),c,5)
    marker_arrow(d,(390,320),(490,320),phase(t,.38),RED,7)
    marker_arrow(d,(790,320),(890,320),phase(t,.58),RED,7)
    if t>.68:
        # Big final stamp pops in
        p=phase(t,.68,.18)
        d.rounded_rectangle((330,500,950,620),radius=22,outline=RED,width=8)
        text_pop(d,(385,530),"¿CASO RESUELTO?",p,48,RED)

RENDERERS=[scene_one,scene_two,scene_three]

def render(output_dir:Path):
    output_dir.mkdir(parents=True,exist_ok=True)
    total=FPS*SCENE_SECONDS*SCENES
    for frame in range(total):
        scene_index=min(frame//(FPS*SCENE_SECONDS),SCENES-1)
        local=frame%(FPS*SCENE_SECONDS)
        t=local/(FPS*SCENE_SECONDS-1)
        im=Image.new("RGB",(WIDTH,HEIGHT),PAPER)
        d=ImageDraw.Draw(im)
        # Fine paper frame and subtle animated marker cursor
        d.rectangle((22,22,WIDTH-22,HEIGHT-22),outline=(225,223,216),width=2)
        RENDERERS[scene_index](d,t)
        # Small red marker tip follows the drawing action.
        if t<.92:
            px=1120-850*t
            py=650-420*abs(math.sin(t*math.pi))
            d.ellipse((px-7,py-7,px+7,py+7),fill=RED)
        # Gentle camera push-in makes the board feel less static.
        zoom=1.0+0.018*math.sin(t*math.pi)
        if zoom>1:
            nw,nh=int(WIDTH*zoom),int(HEIGHT*zoom)
            im=im.resize((nw,nh),Image.Resampling.LANCZOS)
            left=(nw-WIDTH)//2; top=(nh-HEIGHT)//2
            im=im.crop((left,top,left+WIDTH,top+HEIGHT))
        im.save(output_dir/f"frame_{frame:05d}.png",optimize=False)
    return total

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",default="whiteboard_frames")
    args=parser.parse_args()
    count=render(Path(args.output_dir))
    print(f"Rendered {count} frames at {FPS} fps ({count/FPS:.1f} seconds).")

if __name__=="__main__":
    main()
