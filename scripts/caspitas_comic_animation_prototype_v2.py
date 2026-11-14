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
    # Consistent explorer identity across wide, medium and close-up shots.
    if scene==0: cx,base,scale=390,390,0.92
    elif scene==1: cx,base,scale=470,405,1.10
    else: cx,base,scale=410,430,1.28
    def p(x,y): return (int(cx+x*scale),int(base+y*scale))
    sway=math.sin(t*math.tau*.8)
    stride=math.sin(t*math.tau*1.6)*24 if scene==1 else math.sin(t*math.tau*.45)*4
    # soft contact shadow
    d.ellipse((cx-130*scale,base+8*scale,cx+135*scale,base+42*scale),fill=(0,0,0,90))
    # boots and articulated legs with trousers and knee folds
    line(d,[p(-28,8),p(-42+stride,77),p(-62+stride,106)],INK,max(6,int(22*scale)))
    line(d,[p(-28,8),p(-42+stride,77),p(-62+stride,106)],(49,57,62),max(4,int(15*scale)))
    line(d,[p(28,8),p(48-stride,76),p(73-stride,103)],INK,max(6,int(22*scale)))
    line(d,[p(28,8),p(48-stride,76),p(73-stride,103)],(59,65,67),max(4,int(15*scale)))
    for x,y,flip in [(-62+stride,106,-1),(73-stride,103,1)]:
        d.polygon([p(x-18,y-8),p(x+15,y-8),p(x+29*flip,y+7),p(x+20*flip,y+17),p(x-22,y+14)],fill=(30,34,37),outline=INK)
        line(d,[p(x-18,y+12),p(x+20*flip,y+12)],(120,125,122),max(2,int(3*scale)))
    # backpack with seams, side pocket, straps and rolled bedroll
    d.rounded_rectangle((*p(32,-126),*p(116,18)),radius=int(19*scale),fill=(93,70,46),outline=INK,width=max(3,int(5*scale)))
    d.rounded_rectangle((*p(42,-112),*p(106,-56)),radius=int(10*scale),fill=(127,96,57),outline=(33,32,29),width=max(2,int(3*scale)))
    d.rounded_rectangle((*p(49,-157),*p(105,-125)),radius=int(13*scale),fill=(137,109,72),outline=INK,width=max(2,int(4*scale)))
    d.line([p(42,-120),p(25,-75),p(42,8)],fill=(38,39,36),width=max(4,int(9*scale)))
    d.line([p(76,-120),p(90,-80),p(87,8)],fill=(38,39,36),width=max(4,int(8*scale)))
    # coat silhouette, collar and layered shading
    d.polygon([p(-62,-125),p(-43,-151),p(-12,-162),p(30,-149),p(61,-123),p(55,17),p(-54,17)],fill=(43,57,65),outline=INK)
    d.polygon([p(-54,-117),p(-27,-143),p(0,-116),p(26,-143),p(53,-116),p(39,-76),p(-38,-76)],fill=(89,103,107),outline=INK)
    d.line([p(-53,-115),p(-25,-140),p(0,-116),p(27,-140),p(54,-115)],fill=(166,163,143),width=max(2,int(4*scale)))
    d.line([p(0,-115),p(0,8)],fill=(18,27,32),width=max(2,int(3*scale)))
    d.line([p(5,-108),p(5,3)],fill=(126,132,124),width=max(1,int(2*scale)))
    # chest pockets, flaps, stitching and buttons
    for x in (-35,20):
        d.rounded_rectangle((*p(x-13,-54),*p(x+13,-19)),radius=4,fill=(68,82,87),outline=INK,width=max(2,int(3*scale)))
        d.line([p(x-10,-47),p(x+10,-47)],fill=(148,143,122),width=max(1,int(2*scale)))
    for y in (-85,-55,-25):
        d.ellipse((p(0,y)[0]-2,p(0,y)[1]-2,p(0,y)[0]+3,p(0,y)[1]+3),fill=(218,178,91))
    d.line([p(-45,-20),p(-27,4)],fill=(117,126,124),width=max(2,int(3*scale)))
    d.line([p(44,-18),p(28,5)],fill=(117,126,124),width=max(2,int(3*scale)))
    # neck and head, slightly turned three-quarter view
    d.rounded_rectangle((*p(-15,-190),*p(18,-145)),radius=int(7*scale),fill=(190,139,111),outline=INK,width=max(2,int(3*scale)))
    hx,hy=p(-2,-207)
    d.ellipse((hx-39*scale,hy-45*scale,hx+35*scale,hy+47*scale),fill=(226,183,151),outline=INK,width=max(3,int(5*scale)))
    # ear and cheek shadow
    d.ellipse((hx-45*scale,hy-4*scale,hx-30*scale,hy+22*scale),fill=(203,151,122),outline=INK,width=2)
    d.ellipse((hx+15*scale,hy+8*scale,hx+39*scale,hy+32*scale),fill=(183,125,103,100))
    # hair visible below the hat
    d.pieslice((hx-39*scale,hy-53*scale,hx+38*scale,hy+24*scale),180,360,fill=(39,35,32),outline=INK,width=3)
    for ox,oy,r in [(-28,-27,12),(-5,-38,13),(18,-30,12),(29,-7,10)]:
        d.ellipse((hx+(ox-r)*scale,hy+(oy-r)*scale,hx+(ox+r)*scale,hy+(oy+r)*scale),fill=(43,38,34),outline=INK,width=2)
    # explorer hat with crown, band, curved brim and highlight
    d.rounded_rectangle((hx-27*scale,hy-76*scale,hx+25*scale,hy-42*scale),radius=int(7*scale),fill=(111,79,47),outline=INK,width=max(2,int(4*scale)))
    d.ellipse((hx-57*scale,hy-51*scale,hx+59*scale,hy-35*scale),fill=(139,103,61),outline=INK,width=max(2,int(4*scale)))
    d.arc((hx-53*scale,hy-53*scale,hx+54*scale,hy-30*scale),190,345,fill=(213,174,104),width=max(2,int(3*scale)))
    d.line((hx-23*scale,hy-44*scale,hx+22*scale,hy-44*scale),fill=(230,190,106),width=max(2,int(4*scale)))
    # face: brows, eyes, nose, mouth; gaze shifts toward the clue
    eye_y=hy-5*scale
    for ex in (-14,13):
        exx=hx+ex*scale
        d.line((exx-7*scale,eye_y-10*scale,exx+5*scale,eye_y-12*scale),fill=INK,width=max(2,int(3*scale)))
        d.ellipse((exx-4*scale,eye_y-3*scale,exx+4*scale,eye_y+7*scale),fill=(248,239,219),outline=INK,width=1)
        d.ellipse((exx-1*scale,eye_y-1*scale,exx+3*scale,eye_y+6*scale),fill=(39,43,42))
    d.line([ (hx+2*scale,hy+3*scale),(hx+9*scale,hy+19*scale),(hx+3*scale,hy+22*scale) ],fill=(137,88,72),width=max(2,int(3*scale)))
    if scene==2: d.arc((hx-11*scale,hy+24*scale,hx+13*scale,hy+39*scale),190,345,fill=(102,54,45),width=max(2,int(3*scale)))
    else: d.arc((hx-11*scale,hy+22*scale,hx+13*scale,hy+39*scale),10,165,fill=(102,54,45),width=max(2,int(3*scale)))
    # Arms articulated at shoulder and elbow, with natural sleeve folds
    left_shoulder=p(-46,-110)
    if scene==0: left_elbow=p(-78,-48+5*sway); left_hand=p(-95,-8+5*sway)
    elif scene==1: left_elbow=p(-83,-73+16*sway); left_hand=p(-110,-110+14*sway)
    else: left_elbow=p(-70,-70); left_hand=p(-92,-122+4*sway)
    line(d,[left_shoulder,left_elbow],INK,max(5,int(19*scale)))
    line(d,[left_shoulder,left_elbow],(61,75,79),max(4,int(14*scale)))
    line(d,[left_elbow,left_hand],INK,max(4,int(13*scale)))
    line(d,[left_elbow,left_hand],(207,158,127),max(3,int(9*scale)))
    d.ellipse((left_hand[0]-7,left_hand[1]-7,left_hand[0]+8,left_hand[1]+8),fill=(226,183,151),outline=INK,width=2)
    right_shoulder=p(45,-110)
    if scene==0: right_elbow=p(76,-83+6*sway); right_hand=p(104,-50+7*sway)
    elif scene==1: right_elbow=p(80,-95-13*sway); right_hand=p(116,-62-10*sway)
    else: right_elbow=p(72,-78); right_hand=p(110,-118+5*sway)
    line(d,[right_shoulder,right_elbow],INK,max(5,int(19*scale)))
    line(d,[right_shoulder,right_elbow],(61,75,79),max(4,int(14*scale)))
    line(d,[right_elbow,right_hand],INK,max(4,int(13*scale)))
    line(d,[right_elbow,right_hand],(207,158,127),max(3,int(9*scale)))
    d.ellipse((right_hand[0]-8,right_hand[1]-8,right_hand[0]+9,right_hand[1]+9),fill=(226,183,151),outline=INK,width=2)
    # Lantern swings slightly during the walking shot.
    if scene==1:
        lx,ly=left_hand
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
