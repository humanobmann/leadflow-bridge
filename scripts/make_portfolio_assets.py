"""Build Upwork-ready 4:3 cover and vector architecture art.

Generated cover uses an original illustration stored as assets/cover_background.png.
SVG contains editable text/vector overlays; the illustration is a raster layer.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
W, H = 1600, 1200


def font(size: int, bold: bool = False):
    # Prefer Inter, but do not require or redistribute proprietary fonts.
    candidates = (
        ["/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "C:/Windows/Fonts/arialbd.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else
        ["/usr/share/fonts/opentype/inter/Inter-Regular.otf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "C:/Windows/Fonts/arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf"]
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default(size=size)


def cover():
    backdrop = Image.open(ASSETS / "cover_background.png").convert("RGB").resize((W,H),Image.Resampling.LANCZOS)
    backdrop = ImageEnhance.Contrast(backdrop).enhance(1.03).convert("RGBA")
    shade = Image.new("RGBA", (W, H), (0,0,0,0))
    shade_pixels=shade.load()
    for x in range(W):
        alpha=int(200 * (1 - min(x/(W*0.83),1))**1.15 + 33)
        for y in range(H):
            shade_pixels[x,y]=(3,12,24,alpha)
    backdrop.alpha_composite(shade)
    draw=ImageDraw.Draw(backdrop)
    draw.rounded_rectangle((78,72,145,82),radius=5,fill="#6ee4ce")
    draw.text((82,127),"INDEPENDENT PYTHON CASE STUDY",font=font(27,True),fill="#89e4d6",stroke_width=0)
    draw.text((73,278),"CSV to CRM.",font=font(110,True),fill="#ffffff")
    draw.text((73,403),"Without the chaos.",font=font(92,True),fill="#ffffff")
    draw.text((80,575),"Validate records. Retry safely.",font=font(37),fill="#d0e4ed")
    draw.text((80,626),"Keep duplicates out.",font=font(37),fill="#d0e4ed")
    badges=[("PYTHON",188),("REST API",207),("IDEMPOTENCY",286)]
    pos=78
    for label,bw in badges:
        draw.rounded_rectangle((pos,782,pos+bw,848),radius=20,fill=(13,58,74,220),outline="#469d9e",width=2)
        draw.text((pos+23,800),label,font=font(24,True),fill="#d5fcf4")
        pos+=bw+18
    draw.line((80,1062,1520,1062),fill="#4d7180",width=2)
    draw.text((81,1095),"LEADFLOW BRIDGE",font=font(27,True),fill="#f0f6fc")
    draw.text((380,1101),"LOCAL DEMO  /  FICTIONAL DATA  /  NO EXTERNAL CRM",font=font(20),fill="#9cbacc")
    backdrop.convert("RGB").save(ASSETS/"portfolio_cover.png",optimize=True)

    # Self-contained SVG: original illustration embedded as raster base layer,
    # plus editable headings, labels, lines, and chips.
    raw=(ASSETS/"cover_background.png").read_bytes()
    data=base64.b64encode(raw).decode("ascii")
    gradient='''<defs><linearGradient id="dark" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#030c18" stop-opacity=".92"/><stop offset=".55" stop-color="#030c18" stop-opacity=".40"/><stop offset="1" stop-color="#030c18" stop-opacity=".06"/></linearGradient></defs>'''
    labels=''.join(f'<rect x="{x}" y="782" width="{w}" height="66" rx="20" fill="#0d3a4a" fill-opacity=".95" stroke="#469d9e" stroke-width="2"/><text x="{x+23}" y="826" font-size="24" font-weight="700" fill="#d5fcf4">{escape(label)}</text>' for x,w,label in [(78,188,'PYTHON'),(284,207,'REST API'),(509,286,'IDEMPOTENCY')])
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1200" viewBox="0 0 1600 1200">
{gradient}<image x="0" y="0" width="1600" height="1200" preserveAspectRatio="xMidYMid slice" href="data:image/png;base64,{data}"/><rect width="1600" height="1200" fill="url(#dark)"/>
<g font-family="Inter,Arial,sans-serif"><rect x="78" y="72" width="67" height="10" rx="5" fill="#6ee4ce"/>
<text x="82" y="157" font-size="27" letter-spacing="1.2" font-weight="700" fill="#89e4d6">INDEPENDENT PYTHON CASE STUDY</text>
<text x="73" y="374" font-size="110" font-weight="800" fill="#fff">CSV to CRM.</text>
<text x="73" y="498" font-size="92" font-weight="800" fill="#fff">Without the chaos.</text>
<text x="80" y="604" font-size="37" fill="#d0e4ed">Validate records. Retry safely.</text><text x="80" y="656" font-size="37" fill="#d0e4ed">Keep duplicates out.</text>{labels}
<line x1="80" y1="1062" x2="1520" y2="1062" stroke="#4d7180" stroke-width="2"/>
<text x="81" y="1122" font-size="27" font-weight="700" fill="#f0f6fc">LEADFLOW BRIDGE</text>
<text x="380" y="1122" font-size="20" fill="#9cbacc">LOCAL DEMO  /  FICTIONAL DATA  /  NO EXTERNAL CRM</text>
</g></svg>'''
    (ASSETS/"portfolio_cover.svg").write_text(svg,encoding="utf-8")
    print('Cover generated 1600x1200')


def architecture():
    steps=[
        ('01','CSV input','Fictional lead data','source file'),
        ('02','Validate','Strict fields +','normalization'),
        ('03','Send','Bearer token +','bounded retries'),
        ('04','Persist','FastAPI + SQLite','idempotent keys'),
        ('05','Verify','Safe summary +','replay check'),
    ]
    cards=''
    for i,(n,title,small1,small2) in enumerate(steps):
        x=76+302*i
        bg='#e9faf6' if i in (1,3) else '#ffffff'
        cards+=f'''<rect x="{x}" y="380" width="274" height="294" rx="22" fill="{bg}" stroke="#c8dce3" stroke-width="2"/>
        <circle cx="{x+47}" cy="430" r="22" fill="#d5eeec"/>
        <text x="{x+47}" y="441" text-anchor="middle" fill="#177f7e" font-size="22" font-weight="800">{n}</text>
        <text x="{x+22}" y="514" fill="#152f44" font-size="35" font-weight="800">{title}</text>
        <line x1="{x+23}" y1="547" x2="{x+248}" y2="547" stroke="#cadde2" stroke-width="2"/>
        <text x="{x+23}" y="594" fill="#557083" font-size="23">{small1}</text>
        <text x="{x+23}" y="631" fill="#557083" font-size="23">{small2}</text>'''
        if i<4:cards+=f'<path d="M{x+278} 530 h19" fill="none" stroke="#38a69e" stroke-width="5"/><path d="M{x+293} 521 l11 9 -11 9" fill="none" stroke="#38a69e" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1200" viewBox="0 0 1600 1200">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f8fbfd"/><stop offset="1" stop-color="#ebf5f7"/></linearGradient></defs>
<rect width="1600" height="1200" fill="url(#bg)"/>
<g font-family="Inter,Arial,sans-serif"><rect x="76" y="68" width="88" height="9" rx="4" fill="#3dc5ae"/>
<text x="76" y="167" fill="#1c5262" font-size="24" font-weight="800" letter-spacing="1">ARCHITECTURE  /  END TO END</text>
<text x="72" y="276" fill="#132e43" font-size="79" font-weight="800">Five steps. One reliable import.</text>
<text x="76" y="330" fill="#627d8e" font-size="29">A local, reproducible CSV to REST API workflow</text>
{cards}
<rect x="78" y="755" width="699" height="198" rx="24" fill="#14334b"/>
<circle cx="141" cy="814" r="17" fill="#65dfba"/>
<text x="178" y="826" fill="#fff" font-size="32" font-weight="800">Recovery built in</text>
<text x="113" y="886" fill="#b7d4dc" font-size="26">Retry temporary HTTP failures with</text>
<text x="113" y="918" fill="#b7d4dc" font-size="26">bounded delays and safe errors.</text>
<rect x="804" y="755" width="715" height="198" rx="24" fill="#dff4ee" stroke="#b0dbd0" stroke-width="2"/>
<circle cx="867" cy="814" r="17" fill="#219c82"/>
<text x="904" y="826" fill="#153f4b" font-size="32" font-weight="800">Duplicates prevented</text>
<text x="840" y="886" fill="#426875" font-size="26">Identical replay returns existing;</text>
<text x="840" y="918" fill="#426875" font-size="26">conflicting content returns HTTP 409.</text>
<path d="M77 1024 H1519" stroke="#bfd5da" stroke-width="2"/>
<text x="78" y="1086" fill="#335968" font-size="27" font-weight="750">Python · FastAPI · HTTPX · Pydantic · SQLite · Pytest</text>
<text x="78" y="1130" fill="#77909a" font-size="21">Independent demonstration with fictional data. No external CRM or customer deployment.</text>
</g></svg>'''
    (ASSETS/"architecture.svg").write_text(svg,encoding="utf-8")
    cairosvg.svg2png(bytestring=svg.encode("utf-8"),write_to=str(ASSETS/"architecture.png"),output_width=W,output_height=H)
    print('Architecture generated 1600x1200')


if __name__ == '__main__':
    cover()
    architecture()
