
import chisel3._

import approx.addition.{Adder, AdderIO, GeAr}

import emixa.AdderCharacterizer
import emixa.Signedness.Signed
import emixa.Characterization.Random3D

class GeArSpec extends AdderCharacterizer[WrappedGeAr] {
  val sgn = Signed
  val chartype = Random3D

  characterize()
}

class WrappedGeAr(width: Int, subAddWidth: Int, specWidth: Int = 0) extends Adder(width) {
  val gear = Module(new GeAr(width, subAddWidth, specWidth))
  gear.io.a    := io.a
  gear.io.b    := io.b
  gear.io.cin  := io.cin
  gear.io.ctrl := VecInit(Seq.fill(gear.io.ctrl.size)(false.B))
  io.s    := gear.io.s
  io.cout := gear.io.cout
}
