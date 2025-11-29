
package dissertation

import chisel3._

import approx.addition.{
  Adder, FullAdder, SESA1, OFLOCA, GeAr, SklanskyAxPPA, AdaptiveOFLOCA
}
import approx.multiplication.{
  Multiplier, Radix2Multiplier, Radix4Multiplier, AdaptiveRadix2Multiplier
}
import approx.multiplication.comptree.ORCompression

import emixa.{AdderCharacterizer, MultiplierCharacterizer}
import emixa.Signedness._
import emixa.Characterization.Random2D

import scala.reflect.ClassTag
import scala.reflect.runtime.{currentMirror => cm, universe => ru}

/** 
 * Inexact adders
 */

class DissertationAdderSpec[U <: Module](implicit ct: ClassTag[U], tt: ru.TypeTag[U])
  extends AdderCharacterizer[U] {
  val sgn = Signed
  val chartype = Random2D
}

class OFLOCASpec extends DissertationAdderSpec[OFLOCA] {
  characterize()
}
class LSESA1Spec extends DissertationAdderSpec[LSESA1] {
  characterize()
}
class GeArSpec extends DissertationAdderSpec[WrappedGeAr] {
  characterize()
}
class SklanskyAxPPASpec extends DissertationAdderSpec[SklanskyAxPPA] {
  characterize()
}

class AdaptiveOFLOCASpec extends DissertationAdderSpec[WrappedAdaptiveOFLOCA] {
  characterize()
}

class LSESA1(width: Int, approxWidth: Int) extends Adder(width) {
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

class WrappedGeAr(width: Int, subAddWidth: Int, specWidth: Int)
  extends Adder(width) {
  val gear = Module(new GeAr(width, subAddWidth, specWidth))
  gear.io.a    := io.a
  gear.io.b    := io.b
  gear.io.cin  := io.cin
  gear.io.ctrl := VecInit(Seq.fill(gear.io.ctrl.size)(false.B))
  io.s    := gear.io.s
  io.cout := gear.io.cout
}

class WrappedAdaptiveOFLOCA(width: Int, approxWidth: Int, numModes: Int, mode: Int)
  extends Adder(width) {
  val aofloca = Module(new AdaptiveOFLOCA(width, approxWidth, numModes))
  aofloca.io.ctrl := mode.U
  aofloca.io.a    := io.a
  aofloca.io.b    := io.b
  aofloca.io.cin  := io.cin
  io.s    := aofloca.io.s
  io.cout := aofloca.io.cout
}

/** 
 * Inexact multipliers
 */

class DissertationMultiplierSpec[U <: Module](implicit ct: ClassTag[U], tt: ru.TypeTag[U])
  extends MultiplierCharacterizer[U] {
  val sgn = Unsigned
  val chartype = Random2D
}

class R2MORCompSpec extends DissertationMultiplierSpec[R2MORComp] {
  characterize()
}
class R4MORCompSpec extends DissertationMultiplierSpec[R4MORComp] {
  characterize()
}

class AdaptiveR2MSpec extends DissertationMultiplierSpec[WrappedAdaptiveR2M] {
  characterize()
}

class R2MORComp(aWidth: Int, bWidth: Int, approxWidth: Int)
  extends Multiplier(aWidth, bWidth) {
  val r2m = Module(
    new Radix2Multiplier(aWidth, bWidth, comp=true, approx=Seq(ORCompression(approxWidth)))
  )
  io <> r2m.io
}

class R4MORComp(aWidth: Int, bWidth: Int, approxWidth: Int)
  extends Multiplier(aWidth, bWidth) {
  val r4m = Module(
    new Radix4Multiplier(aWidth, bWidth, comp=true, approx=Seq(ORCompression(approxWidth)))
  )
  io <> r4m.io
}

class WrappedAdaptiveR2M(aWidth: Int, bWidth: Int,
  approxWidth: Int, numModes: Int, mode: Int) extends Multiplier(aWidth, bWidth) {
  val ar2m = Module(
    new AdaptiveRadix2Multiplier(aWidth, bWidth, approxWidth, comp=true, numModes=numModes)
  )
  ar2m.io.ctrl := mode.U
  ar2m.io.a    := io.a
  ar2m.io.b    := io.b
  io.p := ar2m.io.p
}
