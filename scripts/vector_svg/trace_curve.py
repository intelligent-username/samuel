import math

a = 2.25
b = 1.35
h = 0.38

# Let's find the exact continuous curve of intersection between S1(u1, v1) and S2(u2, v2)
# Since the curve passes through the origin (0,0,0) and extends toward the rim y = +-b:
# Let's parameterize by s in [-1, 1].
# At s = 0: (0, 0, 0).
# Near s: y ~= b * s.
# S1: x = a*v1*cos(th1), y = b*v1*sin(th1), z = h*v1^1.4*sin(2*th1)
# S2: x = h*v2^1.4*sin(2*th2), y = a*v2*cos(th2), z = b*v2*sin(th2)
# Equating:
# (1) x: a*v1*cos(th1) = h*v2^1.4*sin(2*th2)
# (2) y: b*v1*sin(th1) = a*v2*cos(th2)
# (3) z: h*v1^1.4*sin(2*th1) = b*v2*sin(th2)

# Notice: as s varies from -1 to 1:
# Let's use scipy or a Newton-Raphson solver to trace the exact curve!

def solve_curve():
    points_12 = []
    for step in range(-50, 51):
        s = step / 50.0 # -1 to 1
        target_y = (b - 0.02) * s
        
        # We want a point on S1 and S2 with y ~= target_y
        # Newton-Raphson on (th1, v1, th2, v2)
        # 3 equations (x1=x2, y1=y2, z1=z2) and 1 constraint (y1 = target_y)
        # Let's solve directly:
        best_p = None
        best_err = 1e9
        
        # Grid search around target_y
        for th1_deg in range(-90, 91, 2):
            th1 = math.radians(th1_deg)
            if abs(math.sin(th1)) < 1e-4:
                if abs(target_y) < 1e-3:
                    best_p = (0, 0, 0)
                    best_err = 0
                continue
            v1 = target_y / ((b - 0.02) * math.sin(th1))
            if v1 < 0 or v1 > 1.05:
                continue
            
            # Now point on S1 is fixed:
            cur_a1 = (a - 0.02) * v1
            cur_b1 = (b - 0.02) * v1
            cur_h1 = h * math.pow(v1, 1.4)
            x1 = cur_a1 * math.cos(th1)
            y1 = target_y
            z1 = cur_h1 * math.sin(2 * th1)
            
            # Now find closest point on S2:
            # y1 = a*v2*cos(th2), z1 = b*v2*sin(th2)
            val = (y1 / (a - 0.02))**2 + (z1 / (b - 0.02))**2
            if val > 1.05:
                continue
            v2 = math.sqrt(val)
            th2 = math.atan2(z1 / (b - 0.02), y1 / (a - 0.02))
            x2 = h * math.pow(v2, 1.4) * math.sin(2 * th2)
            
            err = abs(x1 - x2)
            if err < best_err:
                best_err = err
                best_p = ((x1 + x2)*0.5, y1, z1)
                
        if best_p and best_err < 0.05:
            points_12.append((round(best_p[0], 4), round(best_p[1], 4), round(best_p[2], 4)))

    print(f"Traced {len(points_12)} points along S1-S2 intersection:")
    for p in points_12[::10]:
        print(f"  ({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f})")

solve_curve()
