import front

front.segment.exportTemplates()

import external.fan.Centrifugal

full = front.full()
splitter = front.splitter()
foam = front.foam()


filterMale = front.segment.filterSet.male.translate((front.SEGMENT_POSITIONS[0], 0, 0))
filterFemale = front.segment.filterSet.female.translate(
    (front.SEGMENT_POSITIONS[0], 0, 0)
)

segments = full.cut(splitter).solids()
segments = sorted(segments, key=lambda s: (s.Center().x, s.Center().y, s.Center().z))

import export


import front.segment

external.fan.Centrifugal.export()

front.exportForFem()

export.step(filterMale, "male.step")
export.step(filterFemale, "female.step")
export.step(segments[0], "left.step")
export.step(segments[1], "top.step")
export.step(segments[2], "leftBottom.step")
export.step(segments[4], "middleBottom.step")
export.step(segments[8], "rightBottom.step")
