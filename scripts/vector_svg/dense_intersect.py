import math
import numpy as np

a = 2.25
b = 1.35
h = 0.38

# Surface 1 (xy):
# x = (a-0.02)*v1 * cos(th1)
# y = (b-0.02)*v1 * sin(th1)
# z = h * v1^1.4 * sin(2*th1)

# Surface 2 (yz):
# x = h * v2^1.4 * sin(2*th2)
# y = (a-0.02)*v2 * cos(th2)
# z = (b-0.02)*v2 * sin(th2)

# Where do they intersect?
# Let's sample a dense 3D grid of points (x, y, z) and find the level-set intersection:
# F1(x, y, z) = dist to S1
# F2(x, y, z) = dist to S2
# Or sample S1(u, v) and find points where dist(S1(u, v), S2) < epsilon!

print("Sampling S1 and finding distance to S2...")

def s1(u, v):
    theta = u * math.pi * 2
    cur_a = (a - 0.02) * v
    cur_b = (b - 0.02) * v
    cur_h = h * math.pow(v, 1.4)
    return np.array([cur_a * math.cos(theta), cur_b * math.sin(theta), cur_h * math.sin(2 * theta)])

def s2(u, v):
    theta = u * math.pi * 2
    cur_a = (a - 0.02) * v
    cur_b = (b - 0.02) * v
    cur_h = h * math.pow(v, 1.4)
    return np.array([cur_h * math.sin(2 * theta), cur_a * math.cos(theta), cur_b * math.sin(theta)])

# Dense sampling of S2:
s2_pts = []
for j in range(1, 101):
    v = j / 100.0
    for i in range(200):
        u = i / 200.0
        s2_pts.append(s2(u, v))
s2_pts = np.array(s2_pts)

print(f"Generated {len(s2_pts)} points on S2")

# Now check S1 points:
intersect_pts = []
for j in range(10, 101, 2):
    v = j / 100.0
    for i in range(200):
        u = i / 200.0
        p = s1(u, v)
        # Distance to S2
        dists = np.linalg.norm(s2_pts - p, axis=1)
        min_d = np.min(dists)
        if min_d < 0.03:
            intersect_pts.append(p)

intersect_pts = np.array(intersect_pts)
print(f"Found {len(intersect_pts)} near-intersection points")

# Let's inspect the distribution of (x, y, z) in intersect_pts
for p in intersect_pts[::max(1, len(intersect_pts)//15)]:
    print(f"p: x={p[0]:.3f}, y={p[1]:.3f}, z={p[2]:.3f}")
