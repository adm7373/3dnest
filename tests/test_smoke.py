from pathlib import Path

import trimesh

import generate_nest


def test_configured_generation_produces_mesh(tmp_path, monkeypatch):
    config = generate_nest.load_config()
    output_name = tmp_path / "smoke.stl"
    config["output"]["filename"] = str(output_name)
    monkeypatch.chdir(tmp_path)
    mesh = generate_nest.make_shell(
        config["nest"]["outer_radius"],
        config["nest"]["outer_radius"] - config["nest"]["wall_thickness"],
        config["nest"]["center_z"],
        config["nest"]["bottom_z"],
        config["nest"]["top_z"],
        config["output"]["resolution"],
        config["output"].get("vertical_resolution", config["output"]["resolution"] // 2),
    )
    assert len(mesh.faces) > 0
    mesh.export(output_name)
    loaded = trimesh.load(output_name, force="mesh")
    assert len(loaded.faces) > 0
