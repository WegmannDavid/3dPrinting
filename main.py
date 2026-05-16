import external.fan.Centrifugal

import split

v = split.vbar.feature(20, 2)

c = external.fan.Centrifugal.housingVolume()
s = external.fan.Centrifugal.splitter()

segments = c.cut(s).solids()
segments = sorted(segments, key=lambda s: (s.Center().x, s.Center().y, s.Center().z))

import export

export.step(c, "c.step")
export.step(segments[0], "cTop.step")
export.step(segments[1], "cBottom.step")

i = 0
