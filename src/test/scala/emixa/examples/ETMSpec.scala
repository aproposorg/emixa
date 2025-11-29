
import approx.multiplication.ETM

import emixa.MultiplierCharacterizer
import emixa.Signedness.Unsigned
import emixa.Characterization.Random3D

class ETMSpec extends MultiplierCharacterizer[ETM] {
  val sgn = Unsigned
  val chartype = Random3D

  characterize()
}
