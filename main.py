from unittest import result

from front.fanAssembly import fanAssembly
from prelude import *
from ocp_vscode import set_port

set_port(3939)

import front

import helmholtz.array

_fanAssembly = front.fanAssemblySet.fanAssembly
_fanAssemblyCover = front.fanAssemblySet.cover

vanes = front.elbowSet.vanes

_full = front.full()


_solids = front.fullSplit().solids()
_solids = sorted(_solids, key=lambda s: (s.Center().x, s.Center().y, s.Center().z))[:12]


assert len(_solids) == 12, f"Expected 12 solids, got {len(_solids)}"

import os

os.makedirs("build/stl/front", exist_ok=True)

cq.exporters.export(_fanAssembly, "build/stl/front/fanAssembly.stl")
cq.exporters.export(_fanAssemblyCover, "build/stl/front/fanAssemblyCover.stl")

cq.exporters.export(_solids[0], "build/stl/front/left.stl")

cq.exporters.export(_solids[1], "build/stl/front/sec1.stl")
cq.exporters.export(_solids[2], "build/stl/front/sec1top.stl")
cq.exporters.export(_solids[3], "build/stl/front/sec2.stl")
cq.exporters.export(_solids[4], "build/stl/front/sec2top.stl")
cq.exporters.export(_solids[5], "build/stl/front/sec3.stl")
cq.exporters.export(_solids[6], "build/stl/front/sec3top.stl")
cq.exporters.export(_solids[7], "build/stl/front/sec4.stl")
cq.exporters.export(_solids[8], "build/stl/front/sec4top.stl")
cq.exporters.export(_solids[9], "build/stl/front/sec5.stl")
cq.exporters.export(_solids[10], "build/stl/front/sec5top.stl")

cq.exporters.export(_solids[11], "build/stl/front/right.stl")

_fem = front.fem()
_femfoam = front.femFoam()

import export

os.makedirs("build/nas/front", exist_ok=True)


export.combined_nastran(
    shapes=[_fem, _femfoam],
    output_path="build/nas/front/fem.nas",
    max_element_size=10.0,
)
