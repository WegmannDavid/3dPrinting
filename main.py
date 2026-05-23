import front

import external.fan.Centrifugal

external.fan.Centrifugal.export()

full = front.full()
splitter = front.splitter()
foam = front.foam()

segments = full.cut(splitter).solids()
segments = sorted(segments, key=lambda s: (s.Center().x, s.Center().y, s.Center().z))

import export

export.step(segments[0], "left.step")
export.step(segments[1], "leftBottom.step")
export.step(segments[2], "leftTop.step")

front.exportForFem()
