import math

a = 2.25
b = 1.35
h = 0.38

def s1(u, v):
    theta = u * math.pi * 2
    cur_a = (a - 0.02) * v
    cur_b = (b - 0.02) * v
    cur_h = h * math.pow(v, 1.4)
    return (cur_a * math.cos(theta), cur_b * math.sin(theta), cur_h * math.sin(2 * theta))

def s2(u, v):
    theta = u * math.pi * 2
    cur_a = (a - 0.02) * v
    cur_b = (b - 0.02) * v
    cur_h = h * math.pow(v, 1.4)
    return (cur_h * math.sin(2 * theta), cur_a * math.cos(theta), cur_b * math.sin(theta))

# Let's find points where s1(u1, v1) == s2(u2, v2)
# Notice: s1 has x, y, z. s2 has x', y', z'.
# x1 = curA1 * cos(th1)
# y1 = curB1 * sin(th1)
# z1 = curH1 * sin(2*th1)
# x2 = curH2 * sin(2*th2)
# y2 = curA2 * cos(th2)
# z2 = curB2 * sin(th2)

# If we equate y1 = y2:
# (b-0.02)*v1*sin(th1) = (a-0.02)*v2*cos(th2)
# And equate z1 = z2:
# h*v1^1.4*sin(2*th1) = (b-0.02)*v2*sin(th2)
# And equate x1 = x2:
# (a-0.02)*v1*cos(th1) = h*v2^1.4*sin(2*th2)

print("Testing intersection calculation...")

# Let's do a search over u1, v1 and solve for u2, v2
# For a given (u1, v1), can we find if it lies on S2?
# On S2: y/a2 = cos(th2), z/b2 = sin(th2)
# So (y / (a-0.02))^2 + (z / (b-0.02))^2 = v2^2!
# And th2 = atan2(z / (b-0.02), y / (a-0.02))!
# Then we check if x2(v2, th2) == x1!
# Residual = x1 - h * v2^1.4 * sin(2 * th2)!

intersections = []
for i in range(1000):
    u1 = i / 1000.0
    th1 = u1 * math.pi * 2
    # Search v1 in (0, 1]
    # For this u1, is there a v1 where residual(v1) == 0?
    v_best = None
    min_res = 999.0
    for j in range(1, 200):
        v1 = j / 200.0
        p1 = s1(u1, v1)
        x1, y1, z1 = p1
        
        val = (y1 / (a - 0.02))**2 + (z1 / (b - 0.02))**2
        if val > 1.0 or val < 1e-6:
            continue
        v2 = math.sqrt(val)
        th2 = math.atan2(z1 / (b - 0.02), y1 / (a - 0.02))
        x2 = h * math.pow(v2, 1.4) * math.sin(2 * th2)
        res = abs(x1 - x2)
        if res < min_res:
            min_res = res
            v_best = (v1, p1, res)
    if v_best and v_best[2] < 0.02:
        intersections.append(v_best[1])

print(f"Found {len(intersections)} intersection points between S1 and S2")
if intersections:
    print("Sample points:", intersections[:5])
    # Check if x, y, z are non-zero (i.e. curved 3D curve)
    for p in intersections[::max(1, len(intersections)//8)]:
        print(f"  x={p[0]:.3f}, y={p[1]:.3f}, z={p[2]:.3f}")
