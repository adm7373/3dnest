#!/usr/bin/env python3
"""Generate an open spherical nest shell with a flat lower cut."""

from pathlib import Path
import numpy as np
import trimesh
import yaml
from numpy.random import default_rng


def load_config(config_path="config.yaml"):
    with open(config_path, "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def spherical_ring(radius, center_z, z, angles):
    ring_radius = np.sqrt(radius**2 - (z - center_z) ** 2)
    return np.column_stack((
        ring_radius * np.cos(angles),
        ring_radius * np.sin(angles),
        np.full(len(angles), z),
    ))


def make_shell(outer_radius, inner_radius, center_z, bottom_z, top_z, resolution, vertical_resolution):
    """Build a shell between two horizontal planes.

    The upper plane is intentionally left open. The lower plane is closed by
    the planar annulus between the outer and inner spherical rings.
    """
    if not (-outer_radius < bottom_z - center_z < top_z - center_z < outer_radius):
        raise ValueError("bottom_z and top_z must lie inside the outer sphere")
    if not (-inner_radius < bottom_z - center_z < top_z - center_z < inner_radius):
        raise ValueError("bottom_z and top_z must lie inside the inner sphere")
    if resolution < 3:
        raise ValueError("resolution must be at least 3")

    angles = np.linspace(0, 2 * np.pi, resolution, endpoint=False)
    zs = np.linspace(bottom_z, top_z, vertical_resolution + 1)
    outer_rings = [spherical_ring(outer_radius, center_z, z, angles) for z in zs]
    inner_rings = [spherical_ring(inner_radius, center_z, z, angles) for z in zs]
    # Raise the inner sphere's lower cut by one wall thickness. This gives the
    # flat base a real thickness instead of making the inner and outer cuts
    # coincide at the same plane.
    inner_bottom_z = bottom_z + (outer_radius - inner_radius)
    inner_zs = np.linspace(inner_bottom_z, top_z, vertical_resolution + 1)
    inner_rings = [spherical_ring(inner_radius, center_z, z, angles) for z in inner_zs]
    outer_floor_ring = spherical_ring(outer_radius, center_z, inner_bottom_z, angles)
    bottom_center = np.array([[0.0, 0.0, bottom_z]])
    floor_center = np.array([[0.0, 0.0, inner_bottom_z]])
    vertices = np.vstack(outer_rings + inner_rings + [outer_floor_ring, bottom_center, floor_center])
    ring_count = vertical_resolution + 1
    outer_start = 0
    inner_start = ring_count * resolution
    outer_floor_start = ring_count * resolution * 2
    bottom_center_index = len(vertices) - 2
    floor_center_index = len(vertices) - 1
    faces = []

    for row in range(vertical_resolution):
        next_row = row + 1
        for i in range(resolution):
            j = (i + 1) % resolution
            ob = outer_start + row * resolution
            ot = outer_start + next_row * resolution
            ib = inner_start + row * resolution
            it = inner_start + next_row * resolution
            faces.extend([
                [ob + i, ob + j, ot + j], [ob + i, ot + j, ot + i],
                [ib + i, it + j, ib + j], [ib + i, it + i, it + j],
            ])

    # Full flat underside, plus the solid base and its flat interior floor.
    for i in range(resolution):
        j = (i + 1) % resolution
        ob = outer_start + i
        oj = outer_start + j
        ib = inner_start + i
        ij = inner_start + j
        faces.extend([[bottom_center_index, oj, ob]])
        outer_floor = outer_floor_start + i
        outer_floor_j = outer_floor_start + j
        faces.extend([[outer_floor, outer_floor_j, ij], [outer_floor, ij, ib]])
        faces.extend([[floor_center_index, ib, ij]])

        # Top rim closes the wall thickness while leaving the cavity open.
        ob = outer_start + vertical_resolution * resolution + i
        oj = outer_start + vertical_resolution * resolution + j
        ib = inner_start + vertical_resolution * resolution + i
        ij = inner_start + vertical_resolution * resolution + j
        faces.extend([[ob, oj, ij], [ob, ij, ib]])

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)
    mesh.remove_unreferenced_vertices()
    return mesh


def make_torus_section(major_radius, tube_radius, start_angle, span, z, sections=12, tube_sections=8):
    """Create a capped angular section of a torus around the Z axis."""
    u = np.linspace(start_angle, start_angle + span, sections + 1)
    v = np.linspace(0, 2 * np.pi, tube_sections, endpoint=False)
    uu, vv = np.meshgrid(u, v, indexing="ij")
    vertices = np.column_stack(((major_radius + tube_radius * np.cos(vv)).ravel() * np.cos(uu).ravel(),
                                (major_radius + tube_radius * np.cos(vv)).ravel() * np.sin(uu).ravel(),
                                (z + tube_radius * np.sin(vv)).ravel()))
    faces = []
    for i in range(sections):
        for j in range(tube_sections):
            nj = (j + 1) % tube_sections
            a, b = i * tube_sections + j, (i + 1) * tube_sections + j
            faces.extend([[a, b, (i + 1) * tube_sections + nj], [a, (i + 1) * tube_sections + nj, i * tube_sections + nj]])
    # End caps.
    for end in (0, sections):
        base = end * tube_sections
        center = len(vertices)
        vertices = np.vstack((vertices, vertices[base:base + tube_sections].mean(axis=0)))
        for j in range(tube_sections):
            if end == 0:
                faces.append([center, base + (j + 1) % tube_sections, base + j])
            else:
                faces.append([center, base + j, base + (j + 1) % tube_sections])
    return trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)


def make_sticks(config, outer_radius, center_z, bottom_z, top_z):
    sticks = config.get("sticks", {})
    rng = default_rng(sticks.get("seed", 7))
    wall = config["nest"]["wall_thickness"]
    result = []
    for _ in range(sticks.get("count", 0)):
        z = rng.uniform(bottom_z + 2, top_z - 2)
        bowl_radius = np.sqrt(outer_radius**2 - (z - center_z) ** 2)
        tube = rng.uniform(sticks.get("diameter_min", 1.0), sticks.get("diameter_max", 5.0)) / 2
        # Choose a major radius independently from the bowl radius. The torus
        # center is then shifted radially so one edge of its tube touches the
        # bowl wall.
        scale = rng.uniform(
            sticks.get("torus_radius_scale_min", 0.85),
            sticks.get("torus_radius_scale_max", 1.15),
        )
        major = bowl_radius * scale
        exterior = major < bowl_radius
        span = np.deg2rad(rng.uniform(20, 70))
        start = rng.uniform(0, 2 * np.pi)
        stick = make_torus_section(major, tube, start, span, z)
        mid = start + span / 2
        center_offset = bowl_radius - major - tube if exterior else bowl_radius - major + tube
        center_shift = np.array([center_offset * np.cos(mid), center_offset * np.sin(mid), 0.0])
        stick.apply_translation(center_shift)
        tilt = np.deg2rad(rng.uniform(
            sticks.get("horizontal_angle_min_deg", -20.0),
            sticks.get("horizontal_angle_max_deg", 20.0),
        ))
        axis = np.array([-np.sin(mid), np.cos(mid), 0.0])
        pivot = np.array([(major + center_offset) * np.cos(mid),
                          (major + center_offset) * np.sin(mid), z])
        stick.apply_transform(trimesh.transformations.rotation_matrix(tilt, axis, pivot))
        result.append(stick)
    return result


def main():
    config = load_config()
    nest, output = config["nest"], config["output"]
    outer_radius = nest["outer_radius"]
    mesh = make_shell(
        outer_radius,
        outer_radius - nest["wall_thickness"],
        nest["center_z"], nest["bottom_z"], nest["top_z"],
        output["resolution"], output.get("vertical_resolution", output["resolution"] // 2)
    )
    meshes = [mesh] + make_sticks(config, outer_radius, nest["center_z"], nest["bottom_z"], nest["top_z"])
    mesh = trimesh.util.concatenate(meshes)
    output_path = Path(output["filename"])
    mesh.export(output_path)
    print(f"Exported {output_path}")
    print(f"Vertices: {len(mesh.vertices)}, faces: {len(mesh.faces)}")
    print(f"Bounds: {mesh.bounds.tolist()}")
    print(f"Watertight: {mesh.is_watertight}")
    print(f"Winding consistent: {mesh.is_winding_consistent}")


if __name__ == "__main__":
    main()
