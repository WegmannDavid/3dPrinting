import front

import external.fan.Centrifugal
import duct.circular
import duct.bellmouth

b = duct.bellmouth.bellmouthWithStrutsByArea(20, 500, 4)
duct.circular.test(37, 500, 4, 10)

external.fan.Centrifugal.export()

full = front.full()
splitter = front.splitter()
foam = front.foam()

i = 0
