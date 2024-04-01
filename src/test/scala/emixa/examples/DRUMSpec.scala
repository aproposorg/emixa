
import approx.multiplication.DRUM

import emixa.MultiplierCharacterizer
import emixa.Signedness.Signed
import emixa.Characterization.Exhaustive

class DRUMSpec extends MultiplierCharacterizer {
  val sgn = Signed
  val chartype = Exhaustive

  characterize[DRUM]()
}
