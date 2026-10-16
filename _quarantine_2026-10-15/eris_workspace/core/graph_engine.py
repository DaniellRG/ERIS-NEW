"""Graph layout engine — 2 hemispheres like a human brain."""
import math
import random


def layout_brain_hemispheres(nodes, edges, iterations=40, k=0.12):
    positions = {}
    random.seed(42)

    left_nodes = [n for n in nodes if n.hemisphere == "left"]
    right_nodes = [n for n in nodes if n.hemisphere == "right"]

    for i, n in enumerate(left_nodes):
        angle = (i / max(len(left_nodes), 1)) * math.pi * 2
        r = 1.2 + random.uniform(-0.3, 0.3)
        positions[n.id] = [
            -1.8 + r * math.cos(angle) * 0.7,
            r * math.sin(angle) * 0.8,
            random.uniform(-0.5, 0.5),
        ]

    for i, n in enumerate(right_nodes):
        angle = (i / max(len(right_nodes), 1)) * math.pi * 2
        r = 1.2 + random.uniform(-0.3, 0.3)
        positions[n.id] = [
            1.8 + r * math.cos(angle) * 0.7,
            r * math.sin(angle) * 0.8,
            random.uniform(-0.5, 0.5),
        ]

    for _ in range(iterations):
        forces = {nid: [0, 0, 0] for nid in positions}
        nids = list(positions.keys())

        for i in range(len(nids)):
            for j in range(i + 1, len(nids)):
                dx = positions[nids[i]][0] - positions[nids[j]][0]
                dy = positions[nids[i]][1] - positions[nids[j]][1]
                dz = positions[nids[i]][2] - positions[nids[j]][2]
                dist = max(math.sqrt(dx*dx + dy*dy + dz*dz), 0.1)
                rep = k * 1.5 / (dist * dist)
                forces[nids[i]][0] += dx * rep
                forces[nids[i]][1] += dy * rep
                forces[nids[i]][2] += dz * rep
                forces[nids[j]][0] -= dx * rep
                forces[nids[j]][1] -= dy * rep
                forces[nids[j]][2] -= dz * rep

        for e in edges:
            if e.source_id in positions and e.target_id in positions:
                src_node = next((n for n in nodes if n.id == e.source_id), None)
                tgt_node = next((n for n in nodes if n.id == e.target_id), None)
                if not src_node or not tgt_node:
                    continue

                is_cross = src_node.hemisphere != tgt_node.hemisphere
                strength = e.strength * (1.3 if is_cross else 0.8)

                dx = positions[e.source_id][0] - positions[e.target_id][0]
                dy = positions[e.source_id][1] - positions[e.target_id][1]
                dz = positions[e.source_id][2] - positions[e.target_id][2]
                dist = max(math.sqrt(dx*dx + dy*dy + dz*dz), 0.1)
                attr = dist * k * 0.4 * strength
                forces[e.source_id][0] -= dx * attr
                forces[e.source_id][1] -= dy * attr
                forces[e.source_id][2] -= dz * attr
                forces[e.target_id][0] += dx * attr
                forces[e.target_id][1] += dy * attr
                forces[e.target_id][2] += dz * attr

        for nid in positions:
            for axis in range(3):
                f = max(-0.12, min(0.12, forces[nid][axis]))
                positions[nid][axis] += f

        for n in nodes:
            if n.id in positions:
                if n.hemisphere == "left" and positions[n.id][0] > -0.3:
                    positions[n.id][0] -= 0.05
                elif n.hemisphere == "right" and positions[n.id][0] < 0.3:
                    positions[n.id][0] += 0.05

    return positions


def project_3d_to_2d(pos3d, cam_rot_x=25, cam_rot_y=-30, cam_dist=12):
    x, y, z = pos3d
    rx = math.radians(cam_rot_x)
    ry = math.radians(cam_rot_y)
    y2 = y * math.cos(rx) - z * math.sin(rx)
    z2 = y * math.sin(rx) + z * math.cos(rx)
    x2 = x * math.cos(ry) + z2 * math.sin(ry)
    z3 = -x * math.sin(ry) + z2 * math.cos(ry)
    scale = cam_dist / (cam_dist + z3) * 0.8
    return x2 * scale, y2 * scale
