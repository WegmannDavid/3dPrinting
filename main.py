import front

d = front.full()

s = front.splitter()

front.exportForFem()

segments = d.cut(s).solids()
segments = sorted(segments, key=lambda s: (s.Center().x, s.Center().y, s.Center().z))

import export

export.stl(segments[1], "segment1.stl")
export.stl(segments[2], "segment2.stl")
export.stl(segments[3], "segment3.stl")

i = 0
