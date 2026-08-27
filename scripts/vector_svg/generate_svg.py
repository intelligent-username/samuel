import math
import os
import shutil

# --- 3D Vector Math Helpers ---

def normalize(v):
    l = math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
    return (v[0]/l, v[1]/l, v[2]/l) if l > 0 else (0, 0, 0)

def quat_from_axis_angle(axis, angle):
    half = angle * 0.5
    s = math.sin(half)
    return (math.cos(half), axis[0]*s, axis[1]*s, axis[2]*s)

def quat_from_euler(x, y, z):
    c1, s1 = math.cos(x * 0.5), math.sin(x * 0.5)
    c2, s2 = math.cos(y * 0.5), math.sin(y * 0.5)
    c3, s3 = math.cos(z * 0.5), math.sin(z * 0.5)
    return (
        c1*c2*c3 - s1*s2*s3,
        s1*c2*c3 + c1*s2*s3,
        c1*s2*c3 - s1*c2*s3,
        c1*c2*s3 + s1*s2*c3
    )

def quat_multiply(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    )

def quat_rotate_vec(q, v):
    qw, qx, qy, qz = q
    vx, vy, vz = v
    ix =  qw*vx + qy*vz - qz*vy
    iy =  qw*vy + qz*vx - qx*vz
    iz =  qw*vz + qx*vy - qy*vx
    iw = -qx*vx - qy*vy - qz*vz
    return (
        ix*qw + iw*-qx + iy*-qz - iz*-qy,
        iy*qw + iw*-qy + iz*-qx - ix*-qz,
        iz*qw + iw*-qz + ix*-qy - iy*-qx
    )

# Smooth closed Bézier loop from 2D points
def closed_bezier_spline(points, offset_y=0):
    n = len(points)
    if n < 3:
        return ""
    d = []
    p0 = points[0]
    d.append(f"M{p0[0]:.1f} {p0[1] + offset_y:.1f}")

    for i in range(n):
        p_prev = points[(i - 1 + n) % n]
        p_curr = points[i]
        p_next = points[(i + 1) % n]
        p_next2 = points[(i + 2) % n]

        t1x = (p_next[0] - p_prev[0]) / 6.0
        t1y = (p_next[1] - p_prev[1]) / 6.0
        t2x = (p_next2[0] - p_curr[0]) / 6.0
        t2y = (p_next2[1] - p_curr[1]) / 6.0

        cp1x = p_curr[0] + t1x
        cp1y = p_curr[1] + t1y + offset_y
        cp2x = p_next[0] - t2x
        cp2y = p_next[1] - t2y + offset_y
        end_x = p_next[0]
        end_y = p_next[1] + offset_y

        d.append(f" C{cp1x:.1f} {cp1y:.1f}, {cp2x:.1f} {cp2y:.1f}, {end_x:.1f} {end_y:.1f}")

    d.append(" Z")
    return "".join(d)

# Smooth open Bézier spline from 2D points
def open_bezier_spline(points, offset_y=0):
    n = len(points)
    if n < 2:
        return ""
    if n == 2:
        return f"M{points[0][0]:.1f} {points[0][1] + offset_y:.1f} L{points[1][0]:.1f} {points[1][1] + offset_y:.1f}"

    d = [f"M{points[0][0]:.1f} {points[0][1] + offset_y:.1f}"]
    for i in range(n - 1):
        p_prev = points[i - 1] if i > 0 else points[0]
        p_curr = points[i]
        p_next = points[i + 1]
        p_next2 = points[i + 2] if i + 2 < n else p_next

        t1x = (p_next[0] - p_prev[0]) / 6.0
        t1y = (p_next[1] - p_prev[1]) / 6.0
        t2x = (p_next2[0] - p_curr[0]) / 6.0
        t2y = (p_next2[1] - p_curr[1]) / 6.0

        cp1x = p_curr[0] + t1x
        cp1y = p_curr[1] + t1y + offset_y
        cp2x = p_next[0] - t2x
        cp2y = p_next[1] - t2y + offset_y
        d.append(f" C{cp1x:.1f} {cp1y:.1f}, {cp2x:.1f} {cp2y:.1f}, {p_next[0]:.1f} {p_next[1] + offset_y:.1f}")

    return "".join(d)

# --- Exact Borromean Saddle Equations ---
def borromean_point(plane, t, v=1.0, a=2.25, b=1.35, h=0.38):
    theta = t * math.pi * 2
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    cur_a = (a - 0.02) * v if v < 1.0 else a
    cur_b = (b - 0.02) * v if v < 1.0 else b
    cur_h = h * math.pow(v, 1.4)
    saddle = cur_h * math.sin(2 * theta)

    if plane == "xy":
        return (cur_a * cos_t, cur_b * sin_t, saddle)
    elif plane == "yz":
        return (saddle, cur_a * cos_t, cur_b * sin_t)
    else: # zx
        return (cur_b * sin_t, saddle, cur_a * cos_t)

def project(p, width=1920, height=1080, cam_dist=7.6, scale=1220):
    x, y, z = p
    denom = max(0.1, cam_dist - z)
    px = width / 2 + (x / denom) * scale
    py = height / 2 - (y / denom) * scale
    return (round(px, 1), round(py, 1), round(z, 3))

# Generate 3D surface geometry: rim curve + concentric curves + radial ribs
def generate_ring_models():
    planes = ["xy", "yz", "zx"]
    rings = []

    num_radial = 16       # 16 clean radial ribs per ring
    num_concentric = 6    # 6 concentric contours per surface
    u_steps = 36          # 36 points per concentric curve

    for r_idx, plane in enumerate(planes):
        # 1. Concentric closed loops at varying v
        concentric_loops = []
        for c in range(1, num_concentric + 1):
            v = c / num_concentric
            pts = [borromean_point(plane, i / u_steps, v=v) for i in range(u_steps)]
            concentric_loops.append({
                "v": v,
                "points": pts
            })

        # 2. Radial rib curves from center outward
        radial_ribs = []
        v_steps = 8
        for r in range(num_radial):
            t = r / num_radial
            pts = [borromean_point(plane, t, v=j / v_steps) for j in range(v_steps + 1)]
            radial_ribs.append({
                "t": t,
                "points": pts
            })

        # 3. Outer boundary rim (v = 1.0)
        rim_pts = [borromean_point(plane, i / u_steps, v=1.0) for i in range(u_steps)]

        rings.append({
            "ring_idx": r_idx,
            "plane": plane,
            "rim_points": rim_pts,
            "concentric_loops": concentric_loops,
            "radial_ribs": radial_ribs
        })
    return rings

def render_frame_svg(ring_models, q_rot, width=1920, height=1080, offset_y=0):
    svg_elements = []

    # Lighting schemes matching BorromeanBanner.tsx / borromean_snapshot.png:
    # Ring 0: Cyan-backlit saddle mesh
    # Ring 1: Golden-amber front saddle mesh
    # Ring 2: Warm champagne-gold saddle mesh
    ring_schemes = [
        {
            "glow": "rgba(14, 165, 233, 0.14)",
            "wire_conc": "rgba(45, 212, 191, 0.42)",
            "wire_rad": "rgba(56, 189, 248, 0.30)",
            "tube_base": "#bfa054",
            "tube_sheen": "#38bdf8",
            "tube_spec": "#ffffff",
        },
        {
            "glow": "rgba(234, 179, 8, 0.16)",
            "wire_conc": "rgba(245, 158, 11, 0.45)",
            "wire_rad": "rgba(253, 224, 71, 0.30)",
            "tube_base": "#d4b06a",
            "tube_sheen": "#fde047",
            "tube_spec": "#ffffff",
        },
        {
            "glow": "rgba(245, 158, 11, 0.12)",
            "wire_conc": "rgba(212, 176, 106, 0.40)",
            "wire_rad": "rgba(245, 215, 130, 0.28)",
            "tube_base": "#c49a4e",
            "tube_sheen": "#ffd782",
            "tube_spec": "#ffffff",
        }
    ]

    # Calculate 3D projected geometry for all rings
    rendered_rings = []
    for r in ring_models:
        r_idx = r["ring_idx"]
        scheme = ring_schemes[r_idx]

        # Rotate and project rim
        rim_3d = [quat_rotate_vec(q_rot, pt) for pt in r["rim_points"]]
        rim_2d = [project(pt, width, height) for pt in rim_3d]
        avg_z = sum(p[2] for p in rim_3d) / len(rim_3d)

        # Rotate and project concentric loops
        conc_2d = []
        for loop in r["concentric_loops"]:
            pts_3d = [quat_rotate_vec(q_rot, pt) for pt in loop["points"]]
            pts_2d = [project(pt, width, height) for pt in pts_3d]
            conc_2d.append({
                "v": loop["v"],
                "d": closed_bezier_spline(pts_2d, offset_y)
            })

        # Rotate and project radial ribs
        rad_2d = []
        for rib in r["radial_ribs"]:
            pts_3d = [quat_rotate_vec(q_rot, pt) for pt in rib["points"]]
            pts_2d = [project(pt, width, height) for pt in pts_3d]
            rad_2d.append({
                "d": open_bezier_spline(pts_2d, offset_y)
            })

        rendered_rings.append({
            "ring_idx": r_idx,
            "avg_z": avg_z,
            "rim_d": closed_bezier_spline(rim_2d, offset_y),
            "conc_2d": conc_2d,
            "rad_2d": rad_2d,
            "scheme": scheme
        })

    # Sort rings by average Z depth (Painter's algorithm: background to foreground)
    rendered_rings.sort(key=lambda x: x["avg_z"])

    # Render each ring in sorted depth order:
    # 1. Subtle translucent glow wash inside the saddle
    # 2. Parametric 3D concentric curvature wireframe lines
    # 3. Parametric 3D radial rib wireframe lines
    # 4. Smooth continuous metallic tube rim (Shadow + Metallic Tube + Specular Sheen)

    for r in rendered_rings:
        sc = r["scheme"]

        # Atmospheric translucent wash filling the Pringle boundary
        svg_elements.append(
            f'<path d="{r["rim_d"]}" fill="{sc["glow"]}" stroke="none"/>'
        )

        # Concentric curvature wireframe lines
        for c in r["conc_2d"]:
            v = c["v"]
            sw = 1.0 if v > 0.6 else 0.75
            svg_elements.append(
                f'<path d="{c["d"]}" fill="none" stroke="{sc["wire_conc"]}" stroke-width="{sw}"/>'
            )

        # Radial rib lines fanning across the saddle
        for rad in r["rad_2d"]:
            svg_elements.append(
                f'<path d="{rad["d"]}" fill="none" stroke="{sc["wire_rad"]}" stroke-width="0.8"/>'
            )

        # Smooth, continuous metallic tube rim:
        # Layer a: Soft dark ambient shadow behind the tube
        svg_elements.append(
            f'<path d="{r["rim_d"]}" fill="none" stroke="#050301" stroke-width="15.0" stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>'
        )
        # Layer b: Main golden brass metallic pipe
        svg_elements.append(
            f'<path d="{r["rim_d"]}" fill="none" stroke="{sc["tube_base"]}" stroke-width="11.0" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        # Layer c: Studio directional reflection sheen (Cyan or Gold depending on ring)
        svg_elements.append(
            f'<path d="{r["rim_d"]}" fill="none" stroke="{sc["tube_sheen"]}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.80"/>'
        )
        # Layer d: Sharp specular highlight reflection
        svg_elements.append(
            f'<path d="{r["rim_d"]}" fill="none" stroke="{sc["tube_spec"]}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>'
        )

    # Glowing intersection core at the 3D center origin
    center_proj = project(quat_rotate_vec(q_rot, (0, 0, 0)), width, height)
    cx, cy = center_proj[0], center_proj[1] + offset_y
    svg_elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="6" fill="#ffffff" opacity="0.75" filter="url(#centerGlow)"/>'
    )

    return "".join(svg_elements)

def build_vector_banner_svg():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    ring_models = generate_ring_models()

    diag_axis = normalize((0.68, 1.0, 0.46))
    tilt_quat = quat_from_euler(0.48, 0.52, 0.22)

    width = 1920
    height = 1080
    fps = 60
    duration_s = 4.0
    total_frames = int(fps * duration_s) # 240 frames
    total_travel_y = total_frames * height

    defs_content = f'''
    <filter id="centerGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur1"/>
      <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur2"/>
      <feMerge>
        <feMergeNode in="blur1"/>
        <feMergeNode in="blur2"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <clipPath id="viewportClip">
      <rect width="{width}" height="{height}"/>
    </clipPath>
'''

    # 1. Static Master
    print("Generating authentic 3D wireframe static vector SVG...")
    static_content = render_frame_svg(ring_models, tilt_quat, width, height, offset_y=0)
    static_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <defs>{defs_content}</defs>
  <rect width="{width}" height="{height}" fill="#000000"/>
  <g id="borromean-authentic-static">
    {static_content}
  </g>
</svg>'''
    static_path = os.path.join(out_dir, "borromean_static.svg")
    with open(static_path, "w", encoding="utf-8") as f:
        f.write(static_svg)
    print(f"Saved static: {static_path} ({len(static_svg)//1024} KB)")

    # 2. 60 FPS Animated Exact Replica
    print(f"Generating authentic 60 FPS animated vector SVG ({total_frames} frames)...")
    frames_svg = []

    for f_idx in range(total_frames):
        t = f_idx / total_frames
        angle = t * math.pi * 2
        spin_q = quat_from_axis_angle(diag_axis, angle)
        q_frame = quat_multiply(spin_q, tilt_quat)

        offset_y = f_idx * height
        frame_content = render_frame_svg(ring_models, q_frame, width, height, offset_y=offset_y)
        frames_svg.append(f'<g id="f{f_idx}">{frame_content}</g>')

    all_frames = "".join(frames_svg)

    animated_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
  <defs>{defs_content}</defs>
  <style>
    #strip {{
      animation: filmstrip {duration_s}s steps({total_frames}) infinite;
      will-change: transform;
    }}
    @keyframes filmstrip {{
      from {{ transform: translateY(0px); }}
      to {{ transform: translateY(-{total_travel_y}px); }}
    }}
  </style>
  <rect width="{width}" height="{height}" fill="#000000"/>
  <g clip-path="url(#viewportClip)">
    <g id="strip">
      {all_frames}
    </g>
  </g>
</svg>'''
    animated_path = os.path.join(out_dir, "borromean_vector.svg")
    with open(animated_path, "w", encoding="utf-8") as f:
        f.write(animated_svg)
    print(f"Saved 60 FPS animated SVG: {animated_path} ({len(animated_svg)//1024} KB)")

    # 3. Copy to docs/assets/ and frontend/public/
    docs_dir = os.path.join(out_dir, "..", "..", "docs", "assets")
    frontend_dir = os.path.join(out_dir, "..", "..", "frontend", "public")
    for d in [docs_dir, frontend_dir]:
        if os.path.exists(d):
            shutil.copy2(static_path, os.path.join(d, "borromean_vector_static.svg"))
            shutil.copy2(animated_path, os.path.join(d, "borromean_vector_animated.svg"))
            print(f"Copied vector SVGs to {d}")

    # 4. Preview HTML
    preview_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Authentic Borromean Vector Banner (60 FPS)</title>
  <style>
    body {{
      margin: 0;
      background: #000000;
      color: #e5e5eb;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 30px 20px;
    }}
    h1 {{ font-size: 24px; font-weight: 700; color: #d4b06a; margin: 0 0 8px 0; }}
    p {{ color: #888; font-size: 14px; margin: 0 0 24px 0; }}
    .grid {{
      display: flex;
      flex-direction: column;
      gap: 28px;
      width: 100%;
      max-width: 1100px;
    }}
    .card {{
      background: #000000;
      border: 1px solid #1f1f26;
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 16px 48px rgba(0,0,0,0.95);
    }}
    .card-header {{
      padding: 12px 20px;
      font-weight: 600;
      font-size: 13px;
      border-bottom: 1px solid #1f1f26;
      color: #d4b06a;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #0d0d12;
    }}
    .badge {{
      background: rgba(212, 176, 106, 0.15);
      color: #ffd782;
      padding: 3px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
    }}
    .card img {{
      width: 100%;
      height: auto;
      display: block;
      aspect-ratio: 16 / 9;
      background: #000000;
    }}
  </style>
</head>
<body>
  <h1>Authentic Borromean Rings (Pure Vector Edition)</h1>
  <p>True 3D parametric saddle wireframe mesh • Cyan &amp; gold studio reflections • Silky smooth metallic rims • 60 FPS</p>
  
  <div class="grid">
    <div class="card">
      <div class="card-header">
        <span>60 FPS Seamless Loop (Parametric UV Saddle Mesh + Tube Rims)</span>
        <span class="badge">60 FPS • {len(animated_svg)//1024} KB • Pure Vector</span>
      </div>
      <img src="borromean_vector.svg" alt="Animated Borromean Vector 60FPS" />
    </div>
    <div class="card">
      <div class="card-header">
        <span>Static Master Vector (Infinite Resolution)</span>
        <span class="badge">~{len(static_svg)//1024} KB • Crisp Scalable</span>
      </div>
      <img src="borromean_static.svg" alt="Static Borromean Vector" />
    </div>
  </div>
</body>
</html>'''
    preview_path = os.path.join(out_dir, "preview.html")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(preview_html)
    print("Done!")

if __name__ == "__main__":
    build_vector_banner_svg()
