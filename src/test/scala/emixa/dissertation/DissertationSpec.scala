
package dissertation

import chisel3._

import approx.addition.{
  Adder, FullAdder, SESA1, OFLOCA, GeAr, SklanskyAxPPA
}
import approx.multiplication.{Multiplier, Radix2Multiplier, Radix4Multiplier}
import approx.multiplication.comptree.ORCompression

import emixa.{AdderCharacterizer, MultiplierCharacterizer}
import emixa.Signedness._
import emixa.Characterization.Random2D

/** 
 * Inexact adders
 */

class DissertationAdderSpec extends AdderCharacterizer {
  val sgn = Signed
  val chartype = Random2D
}

class OFLOCASpec extends DissertationAdderSpec {
  characterize[OFLOCA]()
}
class LSESA1Spec extends DissertationAdderSpec {
  characterize[LSESA1]()
}
class GeArSpec extends DissertationAdderSpec {
  characterize[WrappedGeAr]()
}
class SklanskyAxPPASpec extends DissertationAdderSpec {
  characterize[SklanskyAxPPA]()
}

private class LSESA1(width: Int, approxWidth: Int) extends Adder(width) {
  val sums = Wire(Vec(width, Bool()))
  val cins = Wire(Vec(width + 1, Bool()))
  cins(0) := io.cin

  // Generate approximate part
  (0 until approxWidth).foreach { i =>
    val add = Module(new SESA1)
    add.io.x   := io.a(i)
    add.io.y   := io.b(i)
    add.io.cin := cins(i)
    sums(i)    := add.io.s
    cins(i+1)  := add.io.cout
  }

  // Generate remaining part
  (approxWidth until width).foreach { i =>
    val add = Module(new FullAdder)
    add.io.x   := io.a(i)
    add.io.y   := io.b(i)
    add.io.cin := cins(i)
    sums(i)    := add.io.s
    cins(i+1)  := add.io.cout
  }

  // Combine results and output
  io.s    := sums.asUInt
  io.cout := cins(width)
}

private class WrappedGeAr(width: Int, subAddWidth: Int, specWidth: Int) extends Adder(width) {
  val gear = Module(new GeAr(width, subAddWidth, specWidth))
  gear.io.a    := io.a
  gear.io.b    := io.b
  gear.io.cin  := io.cin
  gear.io.ctrl := VecInit(Seq.fill(gear.io.ctrl.size)(false.B))
  io.s    := gear.io.s
  io.cout := gear.io.cout
}

/** 
 * Inexact multipliers
 */

class DissertationMultiplierSpec extends MultiplierCharacterizer {
  val sgn = Unsigned
  val chartype = Random2D
}

class R2MORCompSpec extends DissertationMultiplierSpec {
  characterize[R2MORComp]()
}
class R4MORCompSpec extends DissertationMultiplierSpec {
  characterize[R4MORComp]()
}

private class R2MORComp(aWidth: Int, bWidth: Int, approxWidth: Int)
  extends Multiplier(aWidth, bWidth) {
  val r2m = Module(
    new Radix2Multiplier(aWidth, bWidth, comp=true, approx=Seq(ORCompression(approxWidth)))
  )
  io <> r2m.io
}

private class R4MORComp(aWidth: Int, bWidth: Int, approxWidth: Int)
  extends Multiplier(aWidth, bWidth) {
  val r4m = Module(
    new Radix4Multiplier(aWidth, bWidth, comp=true, approx=Seq(ORCompression(approxWidth)))
  )
  io <> r4m.io
}
