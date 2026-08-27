import math

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

tilt = quat_from_euler(0.48, 0.52, 0.22)
print("tilt quat:", [round(x, 6) for x in tilt])

diag_axis = (0.68, 1.0, 0.46)
l = math.sqrt(sum(x*x for x in diag_axis))
axis_norm = [round(x/l, 6) for x in diag_axis]
print("diag axis:", axis_norm)
