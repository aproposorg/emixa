
import approx.addition.OFLOCA

import emixa.AdderCharacterizer
import emixa.Signedness.Signed
import emixa.Characterization.Exhaustive

class OFLOCASpec extends AdderCharacterizer {
  val sgn = Signed
  val chartype = Exhaustive

  characterize[OFLOCA]()
}
