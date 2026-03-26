from unittest import result

from prelude import *
from ocp_vscode import set_port

set_port(3939)

import front

fanAssembly = front.fanAssemblySet.fanAssembly
fanAssemblyCover = front.fanAssemblySet.cover

vanes = front.elbowSet.vanes

_full = front.full()

_fem = front.fem()
_femfoam = front.femFoam()

import export

export.combined_nastran(
    shapes=[_fem, _femfoam],
    output_path="build/nas/system/fem.nas",
    max_element_size=10.0,
)


_solids = front.fullSplit().solids()
_solids = sorted(_solids, key=lambda s: (s.Center().x, s.Center().y, s.Center().z))[:12]


assert len(_solids) == 12, f"Expected 12 solids, got {len(_solids)}"

cq.exporters.export(_solids[0], "build/stl/system/left.stl")

cq.exporters.export(_solids[1], "build/stl/system/sec1.stl")
cq.exporters.export(_solids[2], "build/stl/system/sec1top.stl")
cq.exporters.export(_solids[3], "build/stl/system/sec2.stl")
cq.exporters.export(_solids[4], "build/stl/system/sec2top.stl")
cq.exporters.export(_solids[5], "build/stl/system/sec3.stl")
cq.exporters.export(_solids[6], "build/stl/system/sec3top.stl")
cq.exporters.export(_solids[7], "build/stl/system/sec4.stl")
cq.exporters.export(_solids[8], "build/stl/system/sec4top.stl")
cq.exporters.export(_solids[9], "build/stl/system/sec5.stl")
cq.exporters.export(_solids[10], "build/stl/system/sec5top.stl")

cq.exporters.export(_solids[11], "build/stl/system/right.stl")
