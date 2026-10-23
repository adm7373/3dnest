#!/usr/bin/env python3
"""Generate an open spherical nest shell with a flat lower cut."""

from pathlib import Path
import numpy as np
import trimesh
import yaml


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
    output_path = Path(output["filename"])
    mesh.export(output_path)
    print(f"Exported {output_path}")
    print(f"Vertices: {len(mesh.vertices)}, faces: {len(mesh.faces)}")
    print(f"Bounds: {mesh.bounds.tolist()}")
    print(f"Watertight: {mesh.is_watertight}")
    print(f"Winding consistent: {mesh.is_winding_consistent}")


if __name__ == "__main__":
    main()
