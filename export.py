import gmsh
import cadquery as cq
import tempfile
import os


def stl(shape, name):
    path = os.path.join("./build/stl/", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)  # Handles subfolders too
    if not path.endswith(".stl"):
        path += ".stl"
    cq.exporters.export(shape, path)
    print(f"Exported STL to {path}")


def combined_nastran(shapes: list, output_path: str, max_element_size: float = None):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)  # Handles subfolders too

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)

    if max_element_size is not None:
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", max_element_size)

    all_tags = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for shape_idx, shape in enumerate(shapes):
            solids = shape.solids().vals()

            for solid_idx, solid in enumerate(solids):
                step_path = os.path.join(
                    tmpdir, f"shape_{shape_idx}_solid_{solid_idx}.step"
                )
                cq.exporters.export(cq.Workplane().newObject([solid]), step_path)
                tags = gmsh.model.occ.importShapes(step_path)
                vol_tags = [(3, tag) for dim, tag in tags if dim == 3]
                all_tags.extend(vol_tags)

        gmsh.model.occ.synchronize()

        if len(all_tags) > 1:
            gmsh.model.occ.fragment(all_tags[:1], all_tags[1:])
            gmsh.model.occ.synchronize()

        volumes = gmsh.model.getEntities(3)
        for i, (dim, tag) in enumerate(volumes):
            gmsh.model.addPhysicalGroup(3, [tag], tag=i + 1, name=f"domain_{i+1}")

        gmsh.model.mesh.generate(3)
        gmsh.write(output_path)

    gmsh.finalize()
    print(f"Exported {len(volumes)} domains to {output_path}")
