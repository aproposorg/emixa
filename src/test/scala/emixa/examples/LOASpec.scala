
import chisel3._
import chisel3.experimental.IntParam
import chisel3.util.HasBlackBoxResource

import approx.addition.{Adder, AdderIO}

import emixa.AdderCharacterizer
import emixa.Signedness.Signed
import emixa.Characterization.Random2D

class LOASpec extends AdderCharacterizer {
  val sgn = Signed
  val chartype = Random2D

  characterize[BlackboxLOA]()
}

private class BlackboxLOA(width: Int, approxWidth: Int) extends Adder(width) {
  val rca = Module(new VLOA(width, approxWidth))
  io <> rca.io
}

private class VLOA(val width: Int, val approxWidth: Int)
  extends BlackBox(Map("width" -> IntParam(width), "approxWidth" -> IntParam(approxWidth)))
  with HasBlackBoxResource {
  require(approxWidth <= width)
  val io = IO(new AdderIO(width))
  addResource("/VLOA.v")
}
