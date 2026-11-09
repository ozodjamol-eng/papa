"""Запуск gl-transitions (MIT, github.com/gl-transitions/gl-transitions) из Python через moderngl (EGL, без экрана)."""
import re, numpy as np, moderngl
TDIR = '/home/claude/ext/gl-transitions/transitions/'
W, H = 1080, 1920
_ctx = None; _prog = {}; _vao = {}
def ctx():
    global _ctx
    if _ctx is None: _ctx = moderngl.create_standalone_context(backend='egl')
    return _ctx

VS = """#version 330
in vec2 in_pos; out vec2 uv;
void main(){ uv = in_pos*0.5+0.5; gl_Position = vec4(in_pos,0.,1.); }"""
HEAD = """#version 330
in vec2 uv; out vec4 fragColor;
uniform sampler2D from_tex; uniform sampler2D to_tex;
uniform float progress; uniform float ratio;
vec4 getFromColor(vec2 p){ return texture(from_tex, p); }
vec4 getToColor(vec2 p){ return texture(to_tex, p); }
"""
TAIL = "\nvoid main(){ fragColor = transition(uv); }\n"

def _defaults(src):
    d = {}
    for m in re.finditer(r'uniform\s+(\w+)\s+(\w+)\s*;\s*//\s*=\s*([^\n]+)', src):
        d[m.group(2)] = (m.group(1), m.group(3).strip())
    return d

def prog(name):
    if name in _prog: return _prog[name]
    src = open(TDIR + name + '.glsl').read()
    p = ctx().program(vertex_shader=VS, fragment_shader=HEAD + src + TAIL)
    for k, (typ, val) in _defaults(src).items():
        if k not in p: continue
        nums = [float(x) for x in re.findall(r'-?\d+\.?\d*(?:e-?\d+)?', val)]
        if typ in ('float',): p[k].value = nums[0]
        elif typ == 'int': p[k].value = int(nums[0])
        elif typ == 'bool': p[k].value = 'true' in val
        elif typ.startswith('vec') and nums: p[k].value = tuple(nums[:int(typ[3])]) if len(nums) >= int(typ[3]) else tuple([nums[0]] * int(typ[3]))
        elif typ.startswith('ivec') and nums: p[k].value = tuple(int(x) for x in nums[:int(typ[4])])
    vbo = ctx().buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], 'f4').tobytes())
    _vao[name] = ctx().simple_vertex_array(p, vbo, 'in_pos')
    _prog[name] = p
    return p

_fbo = None; _t = {}
def run(name, A, B, p, **params):
    """A, B: float32 HxWx3 0..1. Возвращает кадр перехода."""
    global _fbo
    c = ctx(); pr = prog(name)
    for k, v in params.items():
        if k in pr: pr[k].value = v
    for key, img in (('from', A), ('to', B)):
        data = (np.clip(img[::-1], 0, 1) * 255).astype('u1').tobytes()
        if key not in _t:
            _t[key] = c.texture((W, H), 3, data); _t[key].repeat_x = _t[key].repeat_y = False
            _t[key].filter = (moderngl.LINEAR, moderngl.LINEAR)
        else: _t[key].write(data)
    if _fbo is None: _fbo = c.simple_framebuffer((W, H), components=3)
    _fbo.use()
    _t['from'].use(0); _t['to'].use(1)
    if 'from_tex' in pr: pr['from_tex'].value = 0
    if 'to_tex' in pr: pr['to_tex'].value = 1
    pr['progress'].value = float(p)
    if 'ratio' in pr: pr['ratio'].value = W / H
    _vao[name].render(moderngl.TRIANGLE_STRIP)
    out = np.frombuffer(_fbo.read(components=3), 'u1').reshape(H, W, 3)[::-1]
    return out.astype(np.float32) / 255
