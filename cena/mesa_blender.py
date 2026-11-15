"""Cena 3D da mesa do hero, renderizada no Blender (Cycles).

Uso:
  blender -b -P cena/mesa_blender.py -- <saida_dir> <largura> <altura> <samples>

Gera <saida_dir>/mesa.png e <saida_dir>/mesa.json. O JSON tem a posição (0..1, origem
no canto superior esquerdo) dos cantos da tela do monitor e das caixas dos objetos
clicáveis, para o HTML encaixar a tela animada e os links por cima da imagem.
"""
import bpy, bmesh, math, json, sys, os
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "cena/out")
RX = int(argv[1]) if len(argv) > 1 else 720
RY = int(argv[2]) if len(argv) > 2 else 600
SAMPLES = int(argv[3]) if len(argv) > 3 else 32
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTO = os.path.join(ROOT, "assets", "img", "pedro.webp")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

# ------------------------------------------------------------------ materiais
def principled(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b is None:  # Blender 5 pode criar o material sem nós
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None) or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return m, b, nt

def setin(bsdf, key, value):
    if key in bsdf.inputs:
        bsdf.inputs[key].default_value = value

def mat(name, color, rough=0.5, metal=0.0, emit=None, strength=0.0, coat=0.0, bump=None):
    m, b, nt = principled(name)
    setin(b, "Base Color", (*color, 1))
    setin(b, "Roughness", rough)
    setin(b, "Metallic", metal)
    if coat:
        setin(b, "Coat Weight", coat)
        setin(b, "Coat Roughness", 0.08)
    if emit:
        setin(b, "Emission Color", (*emit, 1))
        setin(b, "Emission Strength", strength)
    if bump:
        scale, strength_b = bump
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = 8
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = strength_b
        nt.links.new(n.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def wood(name, dark, light, rough=0.5, scale=6.0, bump=0.08, along="X"):
    m, b, nt = principled(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    # Estica o ruído ao longo do comprimento para virar veio de madeira.
    mp.inputs["Scale"].default_value = (0.12, 1.0, 1.0) if along == "X" else (1.0, 1.0, 0.12)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "Y" if along == "X" else "X"
    wv.inputs["Scale"].default_value = scale
    wv.inputs["Distortion"].default_value = 9.0
    wv.inputs["Detail"].default_value = 6.0
    wv.inputs["Detail Roughness"].default_value = 0.7
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 60.0
    nz.inputs["Detail"].default_value = 10.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMath")
    mix.operation = "MULTIPLY_ADD"
    nt.links.new(wv.outputs["Fac"], mix.inputs[0])
    mix.inputs[1].default_value = 0.6
    nt.links.new(nz.outputs["Fac"], mix.inputs[2])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (*light, 1)
    nt.links.new(mix.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.08
    nt.links.new(mix.outputs[0], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.0005
    nt.links.new(mix.outputs[0], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def mug_mat(name, decal_path, height):
    """Cerâmica com o "</>" aplicado por projeção cilíndrica (centrado no +X local)."""
    m, b, nt = principled(name)
    setin(b, "Roughness", 0.12)
    setin(b, "Coat Weight", 0.5)
    setin(b, "Coat Roughness", 0.08)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    ang = nt.nodes.new("ShaderNodeMath"); ang.operation = "ARCTAN2"
    nt.links.new(sep.outputs["Y"], ang.inputs[0]); nt.links.new(sep.outputs["X"], ang.inputs[1])
    u = nt.nodes.new("ShaderNodeMath"); u.operation = "MULTIPLY_ADD"
    nt.links.new(ang.outputs[0], u.inputs[0]); u.inputs[1].default_value = 1 / (2 * math.pi); u.inputs[2].default_value = 0.5
    v = nt.nodes.new("ShaderNodeMath"); v.operation = "DIVIDE"
    nt.links.new(sep.outputs["Z"], v.inputs[0]); v.inputs[1].default_value = height
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(u.outputs[0], comb.inputs["X"]); nt.links.new(v.outputs[0], comb.inputs["Y"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(decal_path)
    tex.extension = "CLIP"
    nt.links.new(comb.outputs["Vector"], tex.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.80, 0.80, 0.78, 1)
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Factor"])
    nt.links.new(tex.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m

def image_mat(name, path):
    m, b, nt = principled(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    setin(b, "Roughness", 0.35)
    # Um pouco de emissão para a foto não sumir no escuro (truque de "luz de destaque").
    nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
    setin(b, "Emission Strength", 0.35)
    return m

SCREEN_GREEN = (0.12, 1.0, 0.32)
M = {
    "desk": wood("desk_wood", (0.006, 0.006, 0.006), (0.040, 0.037, 0.033), rough=0.26, scale=28.0, bump=0.18),
    "steel": mat("black_steel", (0.012, 0.012, 0.013), rough=0.42, metal=0.7),
    "floor": mat("floor", (0.010, 0.014, 0.012), rough=0.85),
    "alu": mat("aluminium", (0.62, 0.64, 0.66), rough=0.28, metal=1.0, bump=(900, 0.03)),
    "bezel": mat("bezel", (0.004, 0.004, 0.004), rough=0.15, coat=0.6),
    "screen": mat("screen", (0, 0, 0), rough=0.2, emit=SCREEN_GREEN, strength=2.2),
    "mat": mat("desk_mat", (0.012, 0.016, 0.014), rough=0.92, bump=(400, 0.15)),
    "kb_case": mat("kb_case", (0.016, 0.017, 0.018), rough=0.38, metal=0.55),
    "keycap": mat("keycap", (0.018, 0.020, 0.019), rough=0.55, bump=(1200, 0.05)),
    "kb_glow": mat("kb_glow", (0, 0, 0), emit=(0.05, 1.0, 0.18), strength=2.5),
    "mouse": mat("mouse", (0.010, 0.011, 0.011), rough=0.32),
    "ceramic": mat("ceramic", (0.80, 0.80, 0.78), rough=0.12, coat=0.5),
    "coffee": mat("coffee", (0.035, 0.014, 0.006), rough=0.05),
    "ink": mat("ink", (0.01, 0.01, 0.01), rough=0.4),
    "leather": mat("leather", (0.010, 0.011, 0.012), rough=0.5, bump=(700, 0.25)),
    "paper": mat("paper", (0.62, 0.56, 0.44), rough=0.9, bump=(80, 0.3)),
    "elastic": mat("elastic", (0.006, 0.006, 0.006), rough=0.35),
    "light_wood": wood("cross_wood", (0.16, 0.07, 0.025), (0.42, 0.20, 0.08), rough=0.45, scale=14.0, bump=0.05, along="Z"),
    "bronze": mat("bronze", (0.80, 0.55, 0.26), rough=0.3, metal=1.0),
    "frame_wood": wood("frame_wood", (0.12, 0.055, 0.022), (0.30, 0.15, 0.06), rough=0.4, scale=18.0, bump=0.04),
    "photo": image_mat("photo", PHOTO),
    "mug": mug_mat("mug_ceramic", os.path.join(ROOT, "cena", "caneca_decal.png"), 0.096),
}

# ------------------------------------------------------------------ geometria
def link(ob, parent=None):
    col.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob

def empty(name, loc=(0, 0, 0), rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.rotation_euler = [math.radians(a) for a in rot]
    return link(e)

def rr_outline(w, d, r, seg=8):
    r = max(1e-4, min(r, w / 2 - 1e-4, d / 2 - 1e-4))
    pts = []
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90),
                       (-w / 2 + r, -d / 2 + r, 180), (w / 2 - r, -d / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def rbox(name, w, d, h, material, loc=(0, 0, 0), r=0.002, bevel=0.0012, parent=None, rot=(0, 0, 0), seg=6):
    """Caixa de cantos arredondados; a origem fica no centro da base."""
    bm = bmesh.new()
    pts = rr_outline(w, d, r, seg)
    bot = [bm.verts.new((x, y, 0)) for x, y in pts]
    top = [bm.verts.new((x, y, h)) for x, y in pts]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = abs(p.normal.z) < 0.5
    me.materials.append(material)
    ob = link(bpy.data.objects.new(name, me), parent)
    ob.location = loc
    ob.rotation_euler = [math.radians(a) for a in rot]
    if bevel > 0:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = min(bevel, h / 2.2)
        mod.segments = 3
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(40)
    return ob

def lathe(name, profile, material, loc=(0, 0, 0), parent=None, steps=72):
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0, z)) for r, z in profile]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=math.radians(360), steps=steps)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(material)
    ob = link(bpy.data.objects.new(name, me), parent)
    ob.location = loc
    return ob

def prim(kind, name, material, parent=None, smooth=True, **kw):
    getattr(bpy.ops.mesh, f"primitive_{kind}_add")(**kw)
    ob = bpy.context.active_object
    ob.name = name
    for c in ob.users_collection:
        c.objects.unlink(ob)
    link(ob, parent)
    ob.data.materials.append(material)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob

TOP = 0.75  # altura do tampo

# --- piso
floor = prim("plane", "floor", M["floor"], size=12, location=(0, 0, 0), smooth=False)
# O piso só serve para rebater luz; na imagem o fundo é transparente e o site aparece por trás.
floor.visible_camera = False

# --- mesa: tampo + pés em "trenó" de aço preto
rbox("desk_top", 1.40, 0.70, 0.028, M["desk"], loc=(0, 0, TOP - 0.028), r=0.004, bevel=0.002)
for sx in (-0.64, 0.64):
    for sy in (-0.30, 0.30):
        rbox("leg", 0.04, 0.04, TOP - 0.028, M["steel"], loc=(sx, sy, 0), r=0.003, bevel=0.001)
    rbox("rail_top", 0.04, 0.64, 0.03, M["steel"], loc=(sx, 0, TOP - 0.058), r=0.003, bevel=0.001)
    rbox("rail_bottom", 0.04, 0.64, 0.03, M["steel"], loc=(sx, 0, 0), r=0.003, bevel=0.001)

# --- monitor (≈ 24")
MON_X, MON_Y = -0.04, 0.17
PANEL_W, PANEL_H, PANEL_T = 0.522, 0.342, 0.018
PANEL_Z = TOP + 0.115
mon = empty("monitor", (MON_X, MON_Y, 0), (0, 0, 0))
rbox("mon_base", 0.24, 0.17, 0.008, M["alu"], loc=(0, 0.02, TOP), r=0.02, bevel=0.002, parent=mon)
rbox("mon_neck", 0.05, 0.022, 0.20, M["alu"], loc=(0, 0.045, TOP + 0.006), r=0.006, bevel=0.002, parent=mon)
panel = rbox("mon_panel", PANEL_W, PANEL_T, PANEL_H, M["alu"], loc=(0, 0.024, PANEL_Z), r=0.004, bevel=0.002, parent=mon)
rbox("mon_bezel", PANEL_W - 0.002, 0.002, PANEL_H - 0.002, M["bezel"], loc=(0, 0.0145, PANEL_Z + 0.001), r=0.003, bevel=0.0006, parent=mon)
SCR_W, SCR_H = PANEL_W - 0.016, PANEL_H - 0.026  # 0.506 x 0.316 = 16:10
screen = prim("plane", "screen", M["screen"], parent=mon, smooth=False, size=1)
screen.scale = (SCR_W, SCR_H, 1)
screen.rotation_euler = (math.radians(90), 0, 0)
screen.location = (0, 0.0132, PANEL_Z + 0.006 + SCR_H / 2 + 0.006)

# --- desk mat
rbox("desk_mat", 0.80, 0.33, 0.003, M["mat"], loc=(0.05, -0.15, TOP), r=0.02, bevel=0.001)

# --- teclado TKL com retroiluminação verde
KB_X, KB_Y, U = -0.03, -0.15, 0.019
kb = empty("keyboard", (KB_X, KB_Y, TOP + 0.003), (0, 0, 0))
KB_W, KB_D = 0.362, 0.136
rbox("kb_case", KB_W, KB_D, 0.020, M["kb_case"], r=0.006, bevel=0.0015, parent=kb)
glow = prim("plane", "kb_glow", M["kb_glow"], parent=kb, smooth=False, size=1)
glow.scale = (KB_W - 0.012, KB_D - 0.012, 1)
glow.location = (0, 0, 0.0203)
rows = [
    [(1, "k"), (1, "gap"), (1, "k"), (1, "k"), (1, "k"), (1, "k"), (0.5, "gap"), (1, "k"), (1, "k"), (1, "k"), (1, "k"),
     (0.5, "gap"), (1, "k"), (1, "k"), (1, "k"), (1, "k"), (0.25, "gap"), (1, "k"), (1, "k"), (1, "k")],
    [(1, "k")] * 13 + [(2, "k"), (0.25, "gap"), (1, "k"), (1, "k"), (1, "k")],
    [(1.5, "k")] + [(1, "k")] * 12 + [(1.5, "k"), (0.25, "gap"), (1, "k"), (1, "k"), (1, "k")],
    [(1.75, "k")] + [(1, "k")] * 11 + [(2.25, "k")],
    [(2.25, "k")] + [(1, "k")] * 10 + [(2.75, "k"), (1.25, "gap"), (1, "k")],
    [(1.25, "k")] * 3 + [(6.25, "k")] + [(1.25, "k")] * 4 + [(0.25, "gap"), (1, "k"), (1, "k"), (1, "k")],
]
total_w = 18.25 * U
y = KB_D / 2 - 0.009 - U / 2
for ri, row in enumerate(rows):
    x = -total_w / 2
    for w, kind in row:
        if kind == "k":
            rbox("key", w * U - 0.0032, U - 0.0032, 0.0105, M["keycap"],
                 loc=(x + w * U / 2, y, 0.0215), r=0.0018, bevel=0.0012, parent=kb)
        x += w * U
    y -= U * (1.5 if ri == 0 else 1.0)

# --- mouse
ms = prim("uv_sphere", "mouse", M["mouse"], segments=48, ring_count=24, radius=1,
          location=(0.30, -0.12, TOP + 0.003))
ms.scale = (0.031, 0.058, 0.021)
prim("cylinder", "mouse_wheel", M["kb_case"], vertices=24, radius=0.0045, depth=0.003,
     location=(0.30, -0.098, TOP + 0.0235), rotation=(0, math.radians(90), 0))

# --- caneca com "</>"
MUG = Vector((-0.50, 0.03, TOP))
cam_loc = Vector((-0.80, -1.95, 1.80))
def facing(p):
    d = cam_loc - Vector((p[0], p[1], 0))
    return math.degrees(math.atan2(d.y, d.x)) + 90

mug = empty("mug", tuple(MUG), (0, 0, facing(MUG) - 90))
R, H = 0.042, 0.096
lathe("mug_body", [(0, 0), (R - 0.004, 0), (R, 0.004), (R, H - 0.002), (R - 0.0015, H),
                   (R - 0.0035, H - 0.002), (R - 0.0035, 0.009), (0, 0.009)], M["mug"], parent=mug)
coffee = prim("cylinder", "coffee", M["coffee"], parent=mug, vertices=64, radius=R - 0.0036, depth=0.002,
              location=(0, 0, H - 0.016))
handle = prim("torus", "mug_handle", M["ceramic"], parent=mug, major_radius=0.026, minor_radius=0.0065,
              major_segments=48, minor_segments=16)
handle.location = (0, -(R + 0.004), H * 0.52)
handle.rotation_euler = (math.radians(90), 0, math.radians(90))
handle.scale = (0.9, 1.25, 1)
mug.rotation_euler.z = math.radians(facing(MUG) - 90 - 14)  # +X local (o "</>") olha para a câmera

# --- caderno preto com elástico
nb = empty("notebook", (-0.47, -0.19, TOP), (0, 0, 8))
NW, ND = 0.148, 0.212
rbox("nb_back", NW, ND, 0.0026, M["leather"], r=0.006, bevel=0.0008, parent=nb)
rbox("nb_pages", NW - 0.008, ND - 0.008, 0.0165, M["paper"], loc=(-0.002, 0, 0.0026), r=0.002, bevel=0.0004, parent=nb)
rbox("nb_front", NW, ND, 0.0026, M["leather"], loc=(0, 0, 0.0191), r=0.006, bevel=0.0008, parent=nb)
rbox("nb_spine", 0.006, ND, 0.0217, M["leather"], loc=(-NW / 2 + 0.002, 0, 0), r=0.0028, bevel=0.0008, parent=nb)
rbox("nb_elastic", 0.007, ND + 0.0016, 0.0225, M["elastic"], loc=(NW / 2 - 0.022, 0, -0.0002), r=0.0006, bevel=0.0003, parent=nb)
rbox("nb_ribbon", 0.006, 0.05, 0.0006, M["elastic"], loc=(-0.02, -ND / 2 - 0.02, 0.0), r=0.0005, bevel=0, parent=nb, rot=(0, 0, 6))

# --- crucifixo de madeira com Cristo em bronze
CR = (0.40, 0.19)
cr = empty("crucifix", (CR[0], CR[1], TOP), (0, 0, facing(CR) - 8))
rbox("cr_base", 0.064, 0.048, 0.014, M["light_wood"], r=0.002, bevel=0.0015, parent=cr)
rbox("cr_base2", 0.044, 0.034, 0.010, M["light_wood"], loc=(0, 0, 0.014), r=0.002, bevel=0.0015, parent=cr)
rbox("cr_post", 0.016, 0.012, 0.21, M["light_wood"], loc=(0, 0, 0.024), r=0.0012, bevel=0.0008, parent=cr)
rbox("cr_beam", 0.106, 0.012, 0.016, M["light_wood"], loc=(0, 0, 0.170), r=0.0012, bevel=0.0008, parent=cr)
FY = -0.0085  # frente da cruz
body = prim("uv_sphere", "corpus_torso", M["bronze"], parent=cr, radius=1, segments=24, ring_count=12,
            location=(0, FY, 0.150))
body.scale = (0.0085, 0.0048, 0.020)
prim("uv_sphere", "corpus_head", M["bronze"], parent=cr, radius=0.0048, segments=24, ring_count=12,
     location=(0.0012, FY - 0.001, 0.1745))
hips = prim("uv_sphere", "corpus_cloth", M["bronze"], parent=cr, radius=1, segments=24, ring_count=12,
            location=(0, FY, 0.130))
hips.scale = (0.0072, 0.0044, 0.006)
for side in (-1, 1):
    arm = prim("cylinder", "corpus_arm", M["bronze"], parent=cr, vertices=12, radius=0.003, depth=0.044)
    arm.location = (side * 0.024, FY, 0.172)
    arm.rotation_euler = (0, math.radians(90 + side * 9), 0)
    leg = prim("cylinder", "corpus_leg", M["bronze"], parent=cr, vertices=12, radius=0.0033, depth=0.042)
    leg.location = (side * 0.0022, FY, 0.106)
    leg.rotation_euler = (0, math.radians(side * -3), 0)

# --- porta-retrato com a foto do Pedro
FR = (0.58, 0.15)
fr = empty("frame", (FR[0], FR[1], TOP), (-11, 0, facing(FR) - 14))
FW, FB, FT = 0.15, 0.017, 0.016
rbox("fr_bottom", FW, FT, FB, M["frame_wood"], loc=(0, 0, 0), r=0.001, bevel=0.0012, parent=fr)
rbox("fr_top", FW, FT, FB, M["frame_wood"], loc=(0, 0, FW - FB), r=0.001, bevel=0.0012, parent=fr)
rbox("fr_left", FB, FT, FW, M["frame_wood"], loc=(-FW / 2 + FB / 2, 0, 0), r=0.001, bevel=0.0012, parent=fr)
rbox("fr_right", FB, FT, FW, M["frame_wood"], loc=(FW / 2 - FB / 2, 0, 0), r=0.001, bevel=0.0012, parent=fr)
rbox("fr_back", FW - 0.004, 0.004, FW - 0.004, M["frame_wood"], loc=(0, 0.006, 0.002), r=0.001, bevel=0.0005, parent=fr)
ph = prim("plane", "photo", M["photo"], parent=fr, smooth=False, size=1)
ph.scale = (FW - 2 * FB + 0.002, FW - 2 * FB + 0.002, 1)
ph.rotation_euler = (math.radians(90), 0, 0)
ph.location = (0, -0.002, FW / 2)
rbox("fr_easel", 0.03, 0.004, 0.12, M["frame_wood"], loc=(0, 0.04, -0.006), r=0.001, bevel=0.0005, parent=fr, rot=(-26, 0, 0))

# ------------------------------------------------------------------ luz e câmera
world = bpy.data.worlds.new("world")
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
wnt = world.node_tree
bg = next((n for n in wnt.nodes if n.type == "BACKGROUND"), None)
if bg is None:
    bg = wnt.nodes.new("ShaderNodeBackground")
    wout = next((n for n in wnt.nodes if n.type == "OUTPUT_WORLD"), None) or wnt.nodes.new("ShaderNodeOutputWorld")
    wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])
bg.inputs["Color"].default_value = (0.0009, 0.0018, 0.0013, 1)
bg.inputs["Strength"].default_value = 1.0

def area(name, loc, target, energy, color, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.size = size
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob

area("rim_cool", (-1.6, 0.9, 1.7), (0, 0, TOP), 30, (0.55, 0.70, 1.0), 1.2)
area("fill_top", (0.2, -0.6, 2.3), (0, 0, TOP), 3, (0.85, 0.95, 0.9), 2.0)
area("back_glow", (0.0, 1.2, 1.1), (0, 0.2, TOP + 0.2), 6, (0.35, 1.0, 0.55), 1.5)

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 61
cam = link(bpy.data.objects.new("cam", cam_data))
cam.location = cam_loc
CAM_TARGET = Vector((0.0, 0.0, 0.86))
cam.rotation_euler = (CAM_TARGET - cam_loc).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

# ------------------------------------------------------------------ render
r = scene.render
r.engine = "CYCLES"
r.resolution_x, r.resolution_y, r.resolution_percentage = RX, RY, 100
r.film_transparent = True
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGBA"
r.filepath = os.path.join(OUT, "mesa.png")
bpy.ops.render.render(write_still=True)

# ------------------------------------------------------------------ posições para o HTML
dg = bpy.context.evaluated_depsgraph_get()
def to2d(co):
    v = world_to_camera_view(scene, cam, co)
    return [round(v.x, 5), round(1 - v.y, 5)]

def bbox(root_name):
    root = bpy.data.objects[root_name]
    pts = []
    for ob in [root] + list(root.children_recursive):
        if ob.type != "MESH":
            continue
        ev = ob.evaluated_get(dg)
        mw = ev.matrix_world
        pts += [to2d(mw @ v.co) for v in ev.data.vertices]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]

sc = screen.evaluated_get(dg)
mw = sc.matrix_world
corners = {}
for v in sc.data.vertices:
    w = mw @ v.co
    key = ("t" if v.co.y > 0 else "b") + ("l" if v.co.x < 0 else "r")
    corners[key] = to2d(w)

data = {
    "size": [RX, RY],
    "screen": [corners["tl"], corners["tr"], corners["br"], corners["bl"]],
    "monitor": bbox("monitor"),
    "notebook": bbox("notebook"),
    "frame": bbox("frame"),
    "mug": bbox("mug"),
    "crucifix": bbox("crucifix"),
    "keyboard": bbox("keyboard"),
}
with open(os.path.join(OUT, "mesa.json"), "w") as f:
    json.dump(data, f, indent=1)
print("OK", json.dumps(data))
