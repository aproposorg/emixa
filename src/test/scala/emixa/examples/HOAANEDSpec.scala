
import approx.addition.HOAANED

import emixa.AdderCharacterizer
import emixa.Signedness.Signed
import emixa.Characterization.Random2D

class HOAANEDSpec extends AdderCharacterizer[HOAANED] {
  val sgn = Signed
  val chartype = Random2D

  characterize()
}
