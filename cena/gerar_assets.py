"""Converte o render do Blender nos arquivos do site.

Uso (da raiz do projeto):
  python3 cena/gerar_assets.py <dir_do_render>

- Gera assets/img/mesa.{avif,webp} (1416px) e mesa-708.{avif,webp} (708px). Precisa do ffmpeg com libaom.
- Lê mesa.json e reescreve o bloco entre "mesa:auto:start" e "mesa:auto:end" em
  assets/css/workspace.css: a matrix3d que encaixa a tela HTML (320x200) nos quatro
  cantos da tela renderizada e a posição dos objetos clicáveis.
"""
import json
import os
import re
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.abspath(sys.argv[1])
DESIGN_W, DESIGN_H = 708, 600   # tamanho da cena em "px de projeto" (o JS escala para o palco)
SCREEN_W, SCREEN_H = 320, 200   # caixa do conteúdo HTML do monitor (16:10)

data = json.load(open(os.path.join(SRC, "mesa.json")))
img = Image.open(os.path.join(SRC, "mesa.png")).convert("RGBA")  # fundo transparente
img.save(os.path.join(ROOT, "assets/img/mesa.webp"), "WEBP", quality=75, method=6)
img.resize((DESIGN_W, DESIGN_H), Image.LANCZOS).save(
    os.path.join(ROOT, "assets/img/mesa-708.webp"), "WEBP", quality=78, method=6)

# AVIF com transparência (cor + canal alfa em fluxos separados): ~55-65% menor que o WebP com a
# mesma qualidade visual. O WebP fica de reserva para navegadores sem AVIF.
for width, name in ((img.width, "mesa.avif"), (DESIGN_W, "mesa-708.avif")):
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", os.path.join(SRC, "mesa.png"),
        "-filter_complex", f"[0:v]scale={width}:-1:flags=lanczos,format=yuva444p,split[c][a];[a]alphaextract[al]",
        "-map", "[c]", "-map", "[al]", "-c:v", "libaom-av1", "-still-picture", "1", "-crf", "32", "-cpu-used", "3",
        os.path.join(ROOT, "assets/img", name),
    ], check=True)


def solve(a, b):
    """Eliminação de Gauss para um sistema 8x8 (sem numpy)."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def homography(dst):
    src = [(0, 0), (SCREEN_W, 0), (SCREEN_W, SCREEN_H), (0, SCREEN_H)]
    a, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = solve(a, b)
    # matrix3d em ordem de coluna, com transform-origin 0 0
    vals = [h[0], h[3], 0, h[6], h[1], h[4], 0, h[7], 0, 0, 1, 0, h[2], h[5], 0, 1]
    return "matrix3d(" + ", ".join(f"{v:.6g}" for v in vals) + ")"


# Cantos da tela em px de projeto, abertos 0,6% a partir do centro para cobrir a borda clara do render.
pts = [(x * DESIGN_W, y * DESIGN_H) for x, y in data["screen"]]
cx = sum(p[0] for p in pts) / 4
cy = sum(p[1] for p in pts) / 4
pts = [(cx + (x - cx) * 1.006, cy + (y - cy) * 1.006) for x, y in pts]


def rect(box, pad=0.006):
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    return (f"left: {x0 * 100:.2f}%; top: {y0 * 100:.2f}%; "
            f"width: {(x1 - x0) * 100:.2f}%; height: {(y1 - y0) * 100:.2f}%;")


block = "\n".join([
    "/* mesa:auto:start (gerado por cena/gerar_assets.py, não editar à mão) */",
    f".desk-monitor {{ transform: {homography(pts)}; }}",
    f".hs-notebook {{ {rect(data['notebook'])} }}",
    f".hs-photo {{ {rect(data['frame'])} }}",
    f".hs-mug {{ {rect(data['mug'])} }}",
    "/* mesa:auto:end */",
])

css_path = os.path.join(ROOT, "assets/css/workspace.css")
css = open(css_path, encoding="utf-8").read()
pattern = re.compile(r"/\* mesa:auto:start.*?mesa:auto:end \*/", re.S)
if not pattern.search(css):
    sys.exit("marcadores mesa:auto não encontrados em workspace.css")
css = pattern.sub(lambda _: block, css)
open(css_path, "w", encoding="utf-8").write(css)
print(block)
for name in ("mesa.avif", "mesa-708.avif", "mesa.webp", "mesa-708.webp"):
    print(name, os.path.getsize(os.path.join(ROOT, "assets/img", name)) // 1024, "KB")
