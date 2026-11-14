from __future__ import annotations
import math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output"/"caspitas-comic-prototype"
W,H,FPS=960,540,12
INK=(18,22,28); SKIN=(224,181,148); COAT=(65,76,78); COAT_LIGHT=(103,111,103)
PACK=(112,86,54); GOLD=(247,190,83); SKY=(22,37,61); SNOW=(183,199,209)
def font(n,b=False):
    p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if b else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p,n) if Path(p).exists() else ImageFont.load_default()
def line(d,pts,fill,width):
    d.line(pts,fill=fill,width=width,joint="curve")
    r=max(2,width//2)
    for x,y in (pts[0],pts[-1]): d.ellipse((x-r,y-r,x+r,y+r),fill=fill)
def background(scene,t):
    im=Image.new("RGB",(W,H),SKY); d=ImageDraw.Draw(im,"RGBA")
    # Layered illustrated landscape, not a floating character on a blank card.
    if scene==0:
        d.rectangle((0,0,W,330),fill=(18,31,53,255))
        d.polygon([(0,320),(170,105),(330,320)],fill=(48,66,81,255))
        d.polygon([(190,320),(490,65),(760,320)],fill=(58,73,83,255))
        d.polygon([(380,320),(700,130),(960,320)],fill=(39,58,73,255))
        d.polygon([(0,365),(960,300),(960,540),(0,540)],fill=(28,39,44,255))
        # cabin and warm window
        d.polygon([(630,285),(820,285),(855,345),(600,345)],fill=(48,39,34,255),outline=INK)
        d.rectangle((635,345,820,460),fill=(75,57,42,255),outline=INK,width=4)
        d.polygon([(605,345),(725,255),(850,345)],fill=(36,37,37,255),outline=INK)
        d.rectangle((680,365,730,420),fill=(255,187,91,255),outline=INK,width=3)
        d.rectangle((755,365,800,420),fill=(255,187,91,255),outline=INK,width=3)
        for x,y in [(85,280),(145,250),(900,275),(520,275)]:
            d.rectangle((x-8,y,x+8,480),fill=(42,34,31,255))
            d.polygon([(x-55,y+35),(x,y-75),(x+55,y+35)],fill=(22,54,52,255))
            d.polygon([(x-45,y-5),(x,y-95),(x+45,y-5)],fill=(31,69,61,255))
    elif scene==1:
        d.rectangle((0,0,W,330),fill=(26,45,70,255))
        d.polygon([(0,360),(210,70),(450,360)],fill=(64,78,87,255))
        d.polygon([(280,360),(650,50),(960,360)],fill=(78,88,91,255))
        d.polygon([(0,405),(960,330),(960,540),(0,540)],fill=(92,104,103,255))
        d.polygon([(0,450),(280,390),(530,450),(960,380),(960,540),(0,540)],fill=(126,139,136,255))
        # snow ridges and distant trail
        d.line([(0,420),(240,385),(420,420),(680,370),(960,405)],fill=(197,209,208,255),width=5)
        d.line([(30,520),(300,465),(510,480),(760,425),(960,455)],fill=(49,66,70,255),width=4)
    else:
        d.rectangle((0,0,W,H),fill=(30,36,45,255))
        # evidence desk, paper, map and lantern
        d.polygon([(0,360),(960,315),(960,540),(0,540)],fill=(71,53,39,255))
        d.polygon([(120,355),(440,300),(540,425),(185,465)],fill=(217,207,183,255),outline=INK)
        for k in range(5):
            y=345+k*18
            d.line((190,y,430,y-30),fill=(111,104,91,255),width=2)
        d.ellipse((730,225,855,350),fill=(255,178,70,60))
        d.rounded_rectangle((760,245,825,365),radius=12,fill=(49,48,42,255),outline=INK,width=4)
        d.rectangle((775,270,810,330),fill=(255,193,93,255))
    # subtle moving mist / snow in foreground
    for i in range(34):
        x=(i*79+int(t*18*(1+i%3)*.25))%W
        y=(i*43+int(math.sin(t+i)*5))%H
        r=1+(i%3)
        d.ellipse((x-r,y-r,x+r,y+r),fill=(220,231,235,70))
    return im
def explorer(im,t,scene):
    d=ImageDraw.Draw(im,"RGBA")
    # Framing changes between wide, medium and close-up, same outfit and identity.
    if scene==0: cx,base,scale=390,385,0.82
    elif scene==1: cx,base,scale=460,395,1.00
    else: cx,base,scale=420,420,1.18
    def p(x,y): return (int(cx+x*scale),int(base+y*scale))
    sway=math.sin(t*math.tau*.8)
    stride=math.sin(t*math.tau*1.6)*20 if scene==1 else math.sin(t*math.tau*.5)*4
    # shadow and legs/boots
    d.ellipse((cx-105*scale,base+10*scale,cx+110*scale,base+35*scale),fill=(0,0,0,85))
    line(d,[p(-28,5),p(-43+stride,82),p(-58+stride,100)],INK,max(5,int(19*scale)))
    line(d,[p(28,5),p(45-stride,78),p(67-stride,98)],INK,max(5,int(19*scale)))
    line(d,[p(-58+stride,100),p(-78+stride,100)],(31,34,37),max(5,int(13*scale)))
    line(d,[p(67-stride,98),p(88-stride,98)],(31,34,37),max(5,int(13*scale)))
    # backpack behind torso
    d.rounded_rectangle((*p(35,-105),*p(105,15)),radius=int(14*scale),fill=PACK,outline=INK,width=max(2,int(4*scale)))
    d.rounded_rectangle((*p(47,-90),*p(92,-55)),radius=int(7*scale),fill=(145,111,67),outline=INK,width=2)
    # jacket, seams, collar, pockets
    d.polygon([p(-55,-112),p(-34,-135),p(32,-135),p(58,-110),p(48,15),p(-48,15)],fill=COAT,outline=INK)
    line(d,[p(-35,-132),p(0,-104),p(32,-132)],(156,157,143),max(2,int(4*scale)))
    line(d,[p(0,-102),p(0,8)],INK,max(1,int(2*scale)))
    for x in (-32,20):
        d.rounded_rectangle((*p(x-12,-45),*p(x+12,-13)),radius=3,fill=COAT_LIGHT,outline=INK,width=2)
    # arms articulate at elbows; right arm reaches toward clue / lantern
    shoulder=p(42,-100)
    if scene==0: elbow=p(70,-72+5*sway); hand=p(95,-35+7*sway)
    elif scene==1: elbow=p(72,-70+12*sway); hand=p(98,-105+12*sway)
    else: elbow=p(64,-75); hand=p(102,-115+5*sway)
    line(d,[shoulder,elbow],INK,max(6,int(17*scale))); line(d,[shoulder,elbow],COAT,max(5,int(13*scale)))
    line(d,[elbow,hand],INK,max(5,int(14*scale))); line(d,[elbow,hand],SKIN,max(4,int(10*scale)))
    d.ellipse((hand[0]-7,hand[1]-7,hand[0]+8,hand[1]+8),fill=SKIN,outline=INK,width=2)
    # neck, face, ears, hair and broad explorer hat
    d.rectangle((*p(-14,-167),*p(14,-130)),fill=SKIN)
    hx,hy=p(0,-185)
    d.ellipse((hx-32*scale,hy-39*scale,hx+32*scale,hy+39*scale),fill=SKIN,outline=INK,width=max(2,int(3*scale)))
    d.ellipse((hx-39*scale,hy-3*scale,hx-28*scale,hy+13*scale),fill=SKIN,outline=INK,width=2)
    d.ellipse((hx+28*scale,hy-3*scale,hx+39*scale,hy+13*scale),fill=SKIN,outline=INK,width=2)
    d.pieslice((hx-34*scale,hy-46*scale,hx+34*scale,hy+7*scale),180,360,fill=(44,39,33),outline=INK,width=2)
    # hat crown + wide brim remains identical across every shot
    d.rounded_rectangle((hx-24*scale,hy-61*scale,hx+24*scale,hy-39*scale),radius=5,fill=(105,79,49),outline=INK,width=2)
    d.ellipse((hx-55*scale,hy-47*scale,hx+55*scale,hy-34*scale),fill=(133,102,61),outline=INK,width=2)
    d.line((hx-26*scale,hy-43*scale,hx+26*scale,hy-43*scale),fill=GOLD,width=2)
    # eyes and brows; gaze changes with the scene
    ey=hy-3*scale
    for ex in (-12,12):
        exx=hx+ex*scale
        d.line((exx-5*scale,ey-8*scale,exx+5*scale,ey-9*scale),fill=INK,width=max(1,int(2*scale)))
        d.ellipse((exx-3*scale,ey-2*scale,exx+3*scale,ey+5*scale),fill=INK)
    if scene==2: d.arc((hx-10*scale,hy+12*scale,hx+10*scale,hy+25*scale),185,350,fill=(94,47,40),width=2)
    else: d.arc((hx-10*scale,hy+11*scale,hx+10*scale,hy+24*scale),10,165,fill=(94,47,40),width=2)
    # small lantern carried in the free hand in scene one
    if scene==1:
        lx,ly=p(-95,-55)
        d.line((lx,ly-20,lx,ly),fill=INK,width=3)
        d.rounded_rectangle((lx-10,ly,lx+10,ly+35),radius=5,fill=(44,43,37),outline=INK,width=2)
        d.rectangle((lx-6,ly+8,lx+6,ly+27),fill=GOLD)
def render():
    OUT.mkdir(parents=True,exist_ok=True)
    frames=8*FPS
    for f in range(frames):
        t=f/FPS; scene=min(2,int(t/8*3))
        im=background(scene,t)
        explorer(im,t,scene)
        d=ImageDraw.Draw(im)
        labels=["LLEGA AL REFUGIO","AVANZA ENTRE LA NIEVE","EXAMINA LAS PISTAS"]
        # minimal editorial caption, no giant floating panel
        d.text((35,28),labels[scene],font=font(20,True),fill=(246,241,226))
        im.save(OUT/f"frame_{f:04d}.png",quality=95)
    target=OUT/"caspitas-comic-animation-prototype.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(OUT/"frame_%04d.png"),
      "-vf","scale=1920:1080:flags=lanczos,format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","19","-movflags","+faststart",str(target)],check=True)
    info=subprocess.check_output(["ffprobe","-v","error","-show_entries","stream=width,height:format=duration","-of","default=noprint_wrappers=1",str(target)],text=True)
    print(info)
    if not target.is_file() or target.stat().st_size<10000: raise SystemExit("MP4 no válido")
if __name__=="__main__": render()
