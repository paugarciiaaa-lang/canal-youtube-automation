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
    if scene==0: cx,base,scale=390,390,0.98
    elif scene==1: cx,base,scale=470,405,1.15
    else: cx,base,scale=410,430,1.28
    def p(x,y): return (int(cx+x*scale),int(base+y*scale))
    sway=math.sin(t*math.tau*.8)
    stride=math.sin(t*math.tau*1.6)*19 if scene==1 else math.sin(t*math.tau*.45)*3
    d.ellipse((cx-140*scale,base+10*scale,cx+145*scale,base+45*scale),fill=(0,0,0,90))
    # Filled trouser legs: articulated silhouettes rather than line limbs.
    left=[p(-34,-3),p(-4,0),p(-19+stride,55),p(-39+stride,99),p(-65+stride,108),p(-54+stride,70)]
    right=[p(4,0),p(35,-4),p(55-stride,55),p(78-stride,98),p(57-stride,109),p(35-stride,72)]
    d.polygon(left,fill=(43,54,62),outline=INK)
    d.polygon(right,fill=(50,61,68),outline=INK)
    d.line([p(-30,-1),p(-25+stride,55),p(-48+stride,91)],fill=(122,129,126),width=max(2,int(3*scale)))
    d.line([p(20,-1),p(40-stride,55),p(64-stride,92)],fill=(124,131,128),width=max(2,int(3*scale)))
    # Full boots with soles and toe caps.
    for x,y,sgn in [(-54+stride,99,-1),(68-stride,99,1)]:
        boot=[p(x-14,y-9),p(x+9,y-9),p(x+18*sgn,y+4),p(x+33*sgn,y+12),p(x+31*sgn,y+22),p(x-20,y+22)]
        d.polygon(boot,fill=(28,33,37),outline=INK)
        d.line([p(x-18,y+19),p(x+28*sgn,y+19)],fill=(139,133,117),width=max(2,int(3*scale)))
    # Backpack behind the torso, with bedroll, seams and straps.
    d.rounded_rectangle((*p(33,-128),*p(120,19)),radius=int(19*scale),fill=(91,69,46),outline=INK,width=max(3,int(5*scale)))
    d.rounded_rectangle((*p(42,-111),*p(109,-54)),radius=int(10*scale),fill=(127,95,58),outline=(30,29,28),width=max(2,int(3*scale)))
    d.rounded_rectangle((*p(49,-164),*p(110,-127)),radius=int(14*scale),fill=(143,111,71),outline=INK,width=max(2,int(4*scale)))
    d.line([p(42,-118),p(24,-72),p(43,8)],fill=(34,35,34),width=max(4,int(9*scale)))
    d.line([p(76,-120),p(93,-75),p(88,8)],fill=(34,35,34),width=max(4,int(8*scale)))
    # Coat torso: broad shoulder silhouette, hem, lapels and panel shading.
    coat=[p(-64,-126),p(-49,-151),p(-16,-164),p(20,-160),p(53,-143),p(66,-119),p(59,19),p(-58,19)]
    d.polygon(coat,fill=(48,63,70),outline=INK)
    d.polygon([p(-56,-117),p(-30,-144),p(0,-118),p(28,-144),p(57,-117),p(40,-73),p(-40,-73)],fill=(91,105,107),outline=INK)
    d.line([p(-56,-117),p(-30,-144),p(0,-118),p(28,-144),p(57,-117)],fill=(174,168,145),width=max(2,int(4*scale)))
    d.polygon([p(-12,-113),p(0,-95),p(12,-113),p(8,14),p(-8,14)],fill=(36,48,53))
    d.line([p(0,-102),p(0,10)],fill=(173,151,112),width=max(2,int(3*scale)))
    for x in (-34,24):
        d.rounded_rectangle((*p(x-13,-55),*p(x+13,-18)),radius=4,fill=(67,82,86),outline=INK,width=max(2,int(3*scale)))
        d.line([p(x-9,-48),p(x+9,-48)],fill=(165,153,127),width=max(1,int(2*scale)))
    for y in (-83,-52,-22):
        xx,yy=p(0,y); d.ellipse((xx-3,yy-3,xx+4,yy+4),fill=(230,187,98))
    d.line([p(-44,-15),p(-28,8)],fill=(129,137,129),width=max(2,int(3*scale)))
    d.line([p(45,-15),p(28,8)],fill=(129,137,129),width=max(2,int(3*scale)))
    # Neck and head, with shaded cheek and three-quarter face.
    d.rounded_rectangle((*p(-15,-193),*p(18,-145)),radius=int(7*scale),fill=(193,142,114),outline=INK,width=max(2,int(3*scale)))
    hx,hy=p(-2,-208)
    d.ellipse((hx-39*scale,hy-47*scale,hx+37*scale,hy+48*scale),fill=(228,185,153),outline=INK,width=max(3,int(5*scale)))
    d.ellipse((hx-47*scale,hy-4*scale,hx-30*scale,hy+23*scale),fill=(206,151,122),outline=INK,width=2)
    d.ellipse((hx+16*scale,hy+10*scale,hx+39*scale,hy+31*scale),fill=(182,125,102,110))
    d.pieslice((hx-40*scale,hy-57*scale,hx+39*scale,hy+25*scale),180,360,fill=(39,34,32),outline=INK,width=3)
    for ox,oy,rx,ry in [(-29,-33,13,15),(-7,-42,14,13),(17,-36,14,16),(31,-13,11,14)]:
        d.ellipse((hx+(ox-rx)*scale,hy+(oy-ry)*scale,hx+(ox+rx)*scale,hy+(oy+ry)*scale),fill=(44,38,34),outline=INK,width=2)
    # Hat with curved brim and crown, consistent across all shots.
    d.rounded_rectangle((hx-28*scale,hy-81*scale,hx+27*scale,hy-43*scale),radius=int(7*scale),fill=(111,79,47),outline=INK,width=max(2,int(4*scale)))
    d.ellipse((hx-61*scale,hy-53*scale,hx+62*scale,hy-34*scale),fill=(142,105,62),outline=INK,width=max(2,int(4*scale)))
    d.arc((hx-54*scale,hy-55*scale,hx+56*scale,hy-30*scale),190,345,fill=(225,184,109),width=max(2,int(3*scale)))
    d.line((hx-24*scale,hy-46*scale,hx+23*scale,hy-46*scale),fill=(231,190,111),width=max(2,int(4*scale)))
    # Eyes, brows, nose and mouth; restrained expressive gaze.
    ey=hy-5*scale
    for ex in (-14,13):
        xx=hx+ex*scale
        d.line((xx-7*scale,ey-11*scale,xx+6*scale,ey-13*scale),fill=INK,width=max(2,int(3*scale)))
        d.ellipse((xx-4*scale,ey-3*scale,xx+4*scale,ey+8*scale),fill=(249,239,218),outline=INK,width=1)
        d.ellipse((xx-1*scale,ey-1*scale,xx+3*scale,ey+7*scale),fill=(38,43,42))
    d.line([(hx+2*scale,hy+3*scale),(hx+10*scale,hy+19*scale),(hx+3*scale,hy+22*scale)],fill=(139,88,71),width=max(2,int(3*scale)))
    d.arc((hx-11*scale,hy+22*scale,hx+14*scale,hy+40*scale),10 if scene==2 else 185,165 if scene==2 else 345,fill=(102,54,45),width=max(2,int(3*scale)))
    # Sleeves are filled, tapered coat shapes; forearms and hands remain separate.
    ls=p(-48,-112)
    if scene==0: le=p(-78,-54+4*sway); lh=p(-98,-11+4*sway)
    elif scene==1: le=p(-83,-76+14*sway); lh=p(-112,-110+12*sway)
    else: le=p(-70,-73); lh=p(-95,-123+4*sway)
    line(d,[p(-48,-112),le],INK,max(5,int(25*scale)))
    line(d,[p(-48,-112),le],(59,75,82),max(4,int(19*scale)))
    d.line([p(-53,-117),le],fill=(144,151,140),width=max(2,int(3*scale)))
    line(d,[le,lh],INK,max(4,int(17*scale)))
    line(d,[le,lh],(213,165,134),max(3,int(13*scale)))
    rs=p(49,-112)
    if scene==0: re=p(78,-84+5*sway); rh=p(108,-51+6*sway)
    elif scene==1: re=p(82,-96-12*sway); rh=p(119,-64-10*sway)
    else: re=p(73,-82); rh=p(112,-121+5*sway)
    line(d,[p(48,-112),re],INK,max(5,int(25*scale)))
    line(d,[p(48,-112),re],(59,75,82),max(4,int(19*scale)))
    d.line([p(53,-117),re],fill=(144,151,140),width=max(2,int(3*scale)))
    line(d,[re,rh],INK,max(4,int(17*scale)))
    line(d,[re,rh],(213,165,134),max(3,int(13*scale)))
    for hand in (lh,rh):
        d.ellipse((hand[0]-8,hand[1]-8,hand[0]+9,hand[1]+9),fill=(228,185,153),outline=INK,width=2)
    if scene==1:
        lx,ly=lh
        d.line((lx,ly-13,lx,ly+3),fill=INK,width=3)
        d.rounded_rectangle((lx-10,ly+3,lx+10,ly+38),radius=5,fill=(43,44,39),outline=INK,width=2)
        d.rectangle((lx-6,ly+10,lx+6,ly+29),fill=(255,194,91))

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
