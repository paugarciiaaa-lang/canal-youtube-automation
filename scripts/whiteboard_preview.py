#!/usr/bin/env python3
"""Caspitas: hand-drawn, varied whiteboard documentary preview."""
from __future__ import annotations
import argparse
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT, FPS = 1280, 720, 24
SCENE_SECONDS = 6
SCENES = 5
PAPER = (252, 251, 247)
INK = (27, 29, 31)
RED = (205, 57, 49)
BLUE = (48, 105, 151)
YELLOW = (224, 169, 48)
GREEN = (62, 126, 91)
GREY = (160, 158, 149)

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
    return p * p * (3 - 2 * p)

def phase(t, start, duration=.22):
    return ease((t - start) / duration)

def stroke(draw, pts, p=1, color=INK, width=6):
    if p <= 0 or len(pts) < 2:
        return
    total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    remaining = total * min(1, p)
    visible = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        length = math.dist(a, b)
        if remaining <= 0:
            break
        f = min(1, remaining / length)
        visible.append((int(a[0] + (b[0]-a[0])*f), int(a[1] + (b[1]-a[1])*f)))
        remaining -= length
        if f < 1:
            break
    if len(visible) > 1:
        draw.line(visible, fill=color, width=width, joint="curve")

def circle(draw, box, p=1, color=INK, width=6):
    if p > 0:
        draw.arc(box, -90, -90 + 360 * min(1, p), fill=color, width=width)

def label(draw, xy, value, p=1, size=30, color=INK, bold=True):
    if p > 0:
        draw.text(xy, value, fill=color, font=font(size, bold))

def arrow(draw, a, b, p=1, color=RED, width=7):
    stroke(draw, [a, b], p, color, width)
    if p >= .95:
        angle = math.atan2(b[1]-a[1], b[0]-a[0])
        left = (b[0]-22*math.cos(angle-.55), b[1]-22*math.sin(angle-.55))
        right = (b[0]-22*math.cos(angle+.55), b[1]-22*math.sin(angle+.55))
        draw.polygon([b, left, right], fill=color)

def stickman(draw, x, y, t, mood="worried", pose="thinking", scale=1.0, color=INK):
    """Original 2D cartoon character with clothes, hair, expressive face and animated gestures."""
    s = scale
    bob = math.sin(t * math.pi * 2) * 3 * s
    top = y + bob
    variant = int(x // 100) % 3
    skin = [(238, 190, 151), (191, 137, 103), (244, 205, 170)][variant]
    hair = [(48, 39, 34), (72, 54, 39), (38, 42, 48)][variant]
    shirt = [BLUE, (183, 83, 65), (74, 119, 88)][variant]
    trousers = [(48, 57, 72), (72, 67, 61), (55, 65, 75)][variant]
    outline = (35, 34, 33)
    sw = max(2, int(4*s))

    # Legs and shoes, drawn behind the body.
    stride = 12 * math.sin(t * math.pi * 2) * s
    hip_y = top + 145*s
    draw.polygon([(x-17*s,hip_y),(x-2*s,hip_y),(x-24*s,top+218*s+stride),(x-42*s,top+218*s+stride)], fill=trousers, outline=outline)
    draw.polygon([(x+2*s,hip_y),(x+18*s,hip_y),(x+39*s,top+218*s-stride),(x+22*s,top+218*s-stride)], fill=trousers, outline=outline)
    draw.ellipse((x-51*s,top+210*s+stride,x-20*s,top+225*s+stride),fill=(42,43,45),outline=outline,width=sw)
    draw.ellipse((x+17*s,top+210*s-stride,x+49*s,top+225*s-stride),fill=(42,43,45),outline=outline,width=sw)

    # Neck and torso: soft, slightly irregular cartoon silhouette.
    draw.rounded_rectangle((x-11*s,top+49*s,x+12*s,top+78*s),radius=int(6*s),fill=skin,outline=outline,width=sw)
    body=[(x-15*s,top+67*s),(x+15*s,top+67*s),(x+31*s,top+139*s),(x+18*s,top+157*s),(x-20*s,top+157*s),(x-32*s,top+139*s)]
    draw.polygon(body,fill=shirt,outline=outline)
    draw.line([(x-15*s,top+77*s),(x-21*s,top+136*s)],fill=(255,255,255),width=max(1,int(2*s)))
    draw.line([(x+15*s,top+77*s),(x+21*s,top+136*s)],fill=(255,255,255),width=max(1,int(2*s)))
    # Small collar detail.
    draw.line([(x-9*s,top+70*s),(x,top+83*s),(x+9*s,top+70*s)],fill=outline,width=sw)

    # Arms with sleeves, elbows and hands. Gestures animate subtly.
    shoulder_y=top+83*s
    wave=9*math.sin(t*math.pi*4)*s
    if pose == "thinking":
        left_elbow=(x-43*s,top+116*s)
        left_hand=(x-12*s,top+69*s)
        right_elbow=(x+43*s,top+111*s)
        right_hand=(x+18*s,top+48*s)
    elif pose == "surprised":
        left_elbow=(x-48*s,top+54*s)
        left_hand=(x-58*s,top+22*s)
        right_elbow=(x+48*s,top+54*s)
        right_hand=(x+58*s,top+22*s)
    elif pose == "pointing":
        left_elbow=(x-43*s,top+119*s)
        left_hand=(x-48*s,top+145*s)
        right_elbow=(x+48*s,top+73*s)
        right_hand=(x+91*s,top+43*s)
    else:
        left_elbow=(x-49*s,top+72*s)
        left_hand=(x-61*s,top+44*s)
        right_elbow=(x+48*s,top+73*s)
        right_hand=(x+62*s,top+39*s+wave)
    for shoulder,elbow,hand in [
        ((x-20*s,shoulder_y),left_elbow,left_hand),
        ((x+20*s,shoulder_y),right_elbow,right_hand)
    ]:
        draw.line([shoulder,elbow,hand],fill=outline,width=max(7,int(17*s)),joint="curve")
        draw.line([shoulder,elbow,hand],fill=skin,width=max(4,int(11*s)),joint="curve")
        draw.ellipse((hand[0]-7*s,hand[1]-7*s,hand[0]+7*s,hand[1]+7*s),fill=skin,outline=outline,width=sw)
        # Tiny fingers make the hand readable at larger sizes.
        if s > .8:
            draw.line([(hand[0],hand[1]),(hand[0]+3*s,hand[1]-9*s)],fill=outline,width=max(1,int(2*s)))

    # Large oval head, ears and hair.
    head=(x-36*s,top-30*s,x+36*s,top+58*s)
    draw.ellipse(head,fill=skin,outline=outline,width=sw)
    draw.ellipse((x-41*s,top+7*s,x-29*s,top+25*s),fill=skin,outline=outline,width=sw)
    draw.ellipse((x+29*s,top+7*s,x+41*s,top+25*s),fill=skin,outline=outline,width=sw)
    # Hair cap and side locks; slight variation by character.
    draw.pieslice((x-38*s,top-37*s,x+38*s,top+34*s),180,360,fill=hair,outline=outline,width=sw)
    if variant == 0:
        draw.polygon([(x-37*s,top+1*s),(x-30*s,top-27*s),(x-13*s,top-36*s),(x-5*s,top-20*s),(x+9*s,top-37*s),(x+30*s,top-24*s),(x+38*s,top+5*s)],fill=hair,outline=outline)
    elif variant == 1:
        draw.ellipse((x-43*s,top-22*s,x-17*s,top+30*s),fill=hair,outline=outline,width=sw)
        draw.ellipse((x+16*s,top-25*s,x+43*s,top+30*s),fill=hair,outline=outline,width=sw)
    else:
        draw.polygon([(x-36*s,top+2*s),(x-29*s,top-31*s),(x+18*s,top-35*s),(x+37*s,top-3*s),(x+26*s,top+8*s)],fill=hair,outline=outline)

    # Expressive eyes, brows and mouth.
    eye_y=top+12*s
    if mood == "worried":
        draw.ellipse((x-19*s,eye_y-5*s,x-7*s,eye_y+10*s),fill=(255,255,250),outline=outline,width=max(1,int(2*s)))
        draw.ellipse((x+7*s,eye_y-5*s,x+19*s,eye_y+10*s),fill=(255,255,250),outline=outline,width=max(1,int(2*s)))
        draw.ellipse((x-13*s,eye_y+1*s,x-7*s,eye_y+8*s),fill=outline)
        draw.ellipse((x+7*s,eye_y+1*s,x+13*s,eye_y+8*s),fill=outline)
        draw.line([(x-22*s,top+1*s),(x-8*s,top-5*s)],fill=outline,width=sw)
        draw.line([(x+8*s,top-5*s),(x+22*s,top+1*s)],fill=outline,width=sw)
        draw.arc((x-9*s,top+32*s,x+10*s,top+52*s),195,345,fill=outline,width=max(2,int(3*s)))
    elif mood == "surprised":
        for ex in (x-13*s,x+13*s):
            draw.ellipse((ex-9*s,eye_y-9*s,ex+9*s,eye_y+13*s),fill=(255,255,250),outline=outline,width=sw)
            draw.ellipse((ex-3*s,eye_y-1*s,ex+3*s,eye_y+7*s),fill=outline)
        draw.ellipse((x-7*s,top+33*s,x+8*s,top+53*s),fill=(75,35,32),outline=outline,width=sw)
    elif mood == "sad":
        draw.ellipse((x-18*s,eye_y-2*s,x-7*s,eye_y+10*s),fill=(255,255,250),outline=outline,width=sw)
        draw.ellipse((x+7*s,eye_y-2*s,x+18*s,eye_y+10*s),fill=(255,255,250),outline=outline,width=sw)
        draw.line([(x-22*s,top+1*s),(x-8*s,top+6*s)],fill=outline,width=sw)
        draw.line([(x+8*s,top+6*s),(x+22*s,top+1*s)],fill=outline,width=sw)
        draw.arc((x-12*s,top+34*s,x+12*s,top+55*s),195,345,fill=outline,width=sw)
    else:
        for ex in (x-13*s,x+13*s):
            draw.ellipse((ex-8*s,eye_y-3*s,ex+8*s,eye_y+10*s),fill=(255,255,250),outline=outline,width=sw)
            draw.ellipse((ex-3*s,eye_y+1*s,ex+3*s,eye_y+7*s),fill=outline)
        draw.arc((x-13*s,top+29*s,x+13*s,top+52*s),5,175,fill=outline,width=sw)

    # A soft cheek highlight gives the faces a finished cartoon look.
    if mood in ("worried","surprised"):
        draw.ellipse((x-27*s,top+29*s,x-18*s,top+35*s),fill=(224,137,122))
        draw.ellipse((x+18*s,top+29*s,x+27*s,top+35*s),fill=(224,137,122))

def magnifier(draw, x, y, p=1, color=BLUE):
    circle(draw,(x-38,y-38,x+38,y+38),p,color,7)
    stroke(draw,[(x+28,y+28),(x+78,y+78)],p,INK,10)

def scene_hook(d,t):
    label(d,(88,55),"HAY UNA PIEZA QUE NO ENCAJA",phase(t,0),43)
    stroke(d,[(90,115),(825,115)],phase(t,.1),YELLOW,8)
    stickman(d,360,245,t,"worried","thinking",1.18)
    label(d,(525,225),"¿Y SI...",phase(t,.22),34,RED)
    label(d,(525,275),"NO FUE ASÍ?",phase(t,.35),38,RED)
    # A clue card is drawn line by line.
    p=phase(t,.3)
    stroke(d,[(850,190),(1140,190),(1140,520),(850,520),(850,190)],p,INK,6)
    label(d,(895,225),"PISTA Nº 1",phase(t,.42),26,BLUE)
    for i,w in enumerate([205,170,225,145]):
        stroke(d,[(895,300+i*42),(895+w,300+i*42)],phase(t,.48+i*.07),GREY,5)
    circle(d,(965,435,1045,515),phase(t,.72),RED,7)
    label(d,(95,600),"A VECES, EL DETALLE MÁS PEQUEÑO LO CAMBIA TODO",phase(t,.78),25,INK)

def scene_map(d,t):
    label(d,(90,48),"RECONSTRUIMOS EL RECORRIDO",phase(t,0),42)
    # Sketchy map contour, route and landmarks.
    stroke(d,[(90,230),(210,175),(350,205),(470,145),(620,205),(760,160),(930,220),(1130,165)],phase(t,.08),GREY,4)
    stroke(d,[(110,475),(250,420),(390,485),(560,410),(710,470),(900,405),(1110,470)],phase(t,.12),GREY,4)
    route=[(150,340),(335,270),(510,355),(690,245),(875,340),(1080,255)]
    for i in range(len(route)-1):
        arrow(d,route[i],route[i+1],phase(t,.18+i*.1,.2),BLUE,7)
    for i,(x,y) in enumerate(route):
        p=phase(t,.22+i*.1,.12)
        if p:
            rad=13+4*math.sin(t*math.pi*6+i)
            d.ellipse((x-rad,y-rad,x+rad,y+rad),outline=RED if i in (0,5) else YELLOW,width=6)
    magnifier(d,int(220+760*min(1,t/.95)),int(510-45*math.sin(t*math.pi*2)),1)
    label(d,(360,585),"CADA LUGAR CUENTA UNA PARTE",phase(t,.65),30,RED)

def scene_evidence(d,t):
    label(d,(90,48),"NO TODAS LAS PRUEBAS PESAN IGUAL",phase(t,0),40)
    # Evidence board: photograph, note, document and connecting string.
    # Photo frame with a simple mountain sketch.
    p=phase(t,.12)
    stroke(d,[(95,190),(365,190),(365,405),(95,405),(95,190)],p,INK,6)
    stroke(d,[(125,350),(190,270),(235,320),(290,235),(340,350)],phase(t,.25),BLUE,5)
    circle(d,(255,210,300,255),phase(t,.32),YELLOW,5)
    label(d,(120,425),"LUGAR",phase(t,.38),24,BLUE)
    # Document
    stroke(d,[(500,175),(755,175),(755,435),(500,435),(500,175)],phase(t,.2),INK,6)
    label(d,(535,205),"INFORME",phase(t,.32),26,RED)
    for i in range(4):
        stroke(d,[(535,270+i*35),(710-(i%2)*35,270+i*35)],phase(t,.4+i*.07),GREY,4)
    # Testimony bubble
    circle(d,(875,190,1150,390),phase(t,.3),INK,6)
    stroke(d,[(930,370),(900,425),(990,390)],phase(t,.42),INK,6)
    label(d,(920,250),"TESTIMONIO",phase(t,.48),24,GREEN)
    label(d,(920,295),"¿FIABLE?",phase(t,.58),30,RED)
    # Connecting strings and a hand-drawn check/cross
    stroke(d,[(365,295),(500,295)],phase(t,.65),RED,5)
    stroke(d,[(755,295),(875,295)],phase(t,.72),RED,5)
    label(d,(270,535),"DOCUMENTOS",phase(t,.78),23,BLUE)
    label(d,(565,535),"CONTRASTAR",phase(t,.82),23,RED)
    label(d,(905,535),"CONTEXTO",phase(t,.86),23,GREEN)

def scene_timeline(d,t):
    label(d,(90,48),"ORDENAMOS LOS HECHOS",phase(t,0),44)
    stroke(d,[(130,365),(1140,365)],phase(t,.12),INK,7)
    events=[(190,"ANTES","Contexto",BLUE),(455,"DURANTE","Hechos",RED),(730,"DESPUÉS","Consecuencias",GREEN),(1030,"HOY","Qué sabemos",YELLOW)]
    for i,(x,top,bottom,c) in enumerate(events):
        p=phase(t,.2+i*.15,.18)
        stroke(d,[(x,365),(x,250 if i%2==0 else 465)],p,c,6)
        circle(d,(x-15,350,x+15,380),p,c,5)
        label(d,(x-80,190 if i%2==0 else 480),top,p,25,c)
        label(d,(x-80,225 if i%2==0 else 515),bottom,p,20,INK,False)
    stickman(d,625,220,t,"neutral","pointing",.62)
    label(d,(390,625),"SEPARAR HECHOS, HIPÓTESIS Y DUDAS",phase(t,.78),27,RED)

def scene_conclusion(d,t):
    label(d,(90,48),"UNA CONCLUSIÓN HONESTA",phase(t,0),44)
    stickman(d,285,245,t,"neutral","pointing",1.0)
    # Three distinct categories instead of a single simplistic reveal.
    boxes=[(510,170,1130,270),(510,315,1130,415),(510,460,1130,560)]
    names=["CONFIRMADO","NO ESTÁ CLARO","SIGUE ABIERTO"]
    colors=[GREEN,YELLOW,RED]
    for i,(box,name,c) in enumerate(zip(boxes,names,colors)):
        x1,y1,x2,y2=box
        p=phase(t,.18+i*.17,.2)
        stroke(d,[(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)],p,INK,5)
        label(d,(x1+28,y1+28),name,p,29,c)
        if p>.8:
            if i==0:
                stroke(d,[(x2-95,y1+55),(x2-75,y1+75),(x2-38,y1+30)],phase(t,.55),GREEN,7)
            elif i==1:
                label(d,(x2-78,y1+17),"?",phase(t,.55),58,YELLOW)
            else:
                circle(d,(x2-88,y1+18,x2-35,y1+71),phase(t,.55),RED,6)
    label(d,(125,605),"NO INVENTAMOS RESPUESTAS. SEGUIMOS LAS PRUEBAS.",phase(t,.78),25,INK)

RENDERERS=[scene_hook,scene_map,scene_evidence,scene_timeline,scene_conclusion]

def render(output_dir:Path):
    output_dir.mkdir(parents=True,exist_ok=True)
    total=FPS*SCENE_SECONDS*SCENES
    for frame in range(total):
        scene_index=min(frame//(FPS*SCENE_SECONDS),SCENES-1)
        local=frame%(FPS*SCENE_SECONDS)
        t=local/(FPS*SCENE_SECONDS-1)
        im=Image.new("RGB",(WIDTH,HEIGHT),PAPER)
        d=ImageDraw.Draw(im)
        d.rectangle((22,22,WIDTH-22,HEIGHT-22),outline=(226,224,216),width=2)
        # Faint paper grain gives a subtle hand-drawn board texture.
        for gx in range(48,WIDTH,160):
            for gy in range(48,HEIGHT,150):
                d.ellipse((gx,gy,gx+2,gy+2),fill=(238,236,229))
        RENDERERS[scene_index](d,t)
        # A small marker tip follows the drawing sequence.
        if t<.94:
            px=1120-820*t
            py=650-340*abs(math.sin(t*math.pi))
            d.ellipse((px-6,py-6,px+6,py+6),fill=RED)
        # Gentle camera drift changes framing without making text hard to read.
        zoom=1.0+0.012*math.sin(t*math.pi)
        if zoom>1:
            nw,nh=int(WIDTH*zoom),int(HEIGHT*zoom)
            im=im.resize((nw,nh),Image.Resampling.LANCZOS)
            left=(nw-WIDTH)//2
            top=(nh-HEIGHT)//2
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
