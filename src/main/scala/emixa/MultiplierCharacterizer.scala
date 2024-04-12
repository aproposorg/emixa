
package emixa
import Characterization._
import Signedness._

import chisel3._
import chiseltest._
import chisel3.util.log2Up

import scala.collection.mutable

import approx.multiplication.Multiplier

abstract class MultiplierCharacterizer extends Characterizer {
  private[emixa] def _characterize[T <: Module](mod: T): Unit = mod match {
    case mult: Multiplier =>
      chartype match {
        case Exhaustive => _charExhaustive(mult)
        case Random2D   => _charRand2D(mult)
        case Random3D   => _charRand3D(mult)
      }
    case other => throw new IllegalArgumentException(s"cannot characterize module $other")
  }

  private[MultiplierCharacterizer] def _charExhaustive[T <: Multiplier](mod: T): Unit = {
    assume(mod.aWidth <= 10 && mod.bWidth <= 10,
      "cannot exhaustively characterize multipliers with more than 10-bit inputs")
    assume(mod.aWidth == mod.bWidth, "cannot characterize multipliers with non-equal input bit-widths")
    val pWidth = mod.aWidth + mod.bWidth

    // Write something to the terminal
    println(s"${_info} $chartype $sgn multiplier characterization")

    /** Optionally sign-extend a result from the multiplier */
    def sext(num: BigInt): BigInt = sgn match {
      case Signed => if (num.testBit(pWidth-1)) (BigInt(-1) << pWidth) | num else num
      case _ => num
    }

    // Run through all input combinations and store the error distance results
    val mask = ((BigInt(1) << pWidth) - 1)
    val results = (0 until (1 << mod.aWidth)).flatMap { a =>
      mod.io.a.poke(a.U)
      (0 until (1 << mod.aWidth)).map { b =>
        mod.io.b.poke(b.U)
        // Optionally sign-extend product and result and return the difference
        val (ga, gb) = (BigInt(a), BigInt(b))
        val prd = sext((sgn match {
          case Signed =>
            val xa = if (ga.testBit(mod.aWidth-1)) (BigInt(-1) << mod.aWidth) | ga else ga
            val xb = if (gb.testBit(mod.bWidth-1)) (BigInt(-1) << mod.bWidth) | gb else gb
            xa * xb
          case _ => ga * gb
        }) & mask)
        val res = sext(mod.io.p.peek().litValue)
        res - prd
      }
    }

    // Output results to a binary file
    _writeExhaustive(results.toArray, mod.aWidth, mod.bWidth)
    println(s"${_info} Wrote results to $path/errors.bin")
  }

  private[MultiplierCharacterizer] def _charRand2D[T <: Multiplier](mod: T): Unit = {
    assume(mod.aWidth <= 64 && mod.bWidth <= 64,
      "cannot randomly characterize multipliers with more than 64-bit inputs")
    assume(mod.aWidth == mod.bWidth, "cannot characterize multipliers with non-equal input bit-widths")
    val pWidth = mod.aWidth + mod.bWidth

    // Write something to the terminal
    println(s"${_info} $chartype $sgn multiplier characterization")

    /** Optionally sign-extend a result from the multiplier */
    def sext(num: BigInt): BigInt = sgn match {
      case Signed => if (num.testBit(pWidth-1)) (BigInt(-1) << pWidth) | num else num
      case _ => num
    }

    // Run through a load of random input combinations and store the
    // error results per result
    val mask = ((BigInt(1) << pWidth) - 1)
    val rng  = new scala.util.Random(42)
    val results = mutable.Map.empty[BigInt, mutable.ArrayBuffer[BigInt]]
    if (mod.aWidth <= 10) { // exhaustive run
      for (a <- 0 until (1 << mod.aWidth); b <- 0 until (1 << mod.aWidth)) {
        mod.io.a.poke(a.U)
        mod.io.b.poke(b.U)
        // Optionally sign-extend product and result and compute the difference
        val (ga, gb) = (BigInt(a), BigInt(b))
        val prd = sext((sgn match {
          case Signed =>
            val xa = if (ga.testBit(mod.aWidth-1)) (BigInt(-1) << mod.aWidth) | ga else ga
            val xb = if (gb.testBit(mod.bWidth-1)) (BigInt(-1) << mod.bWidth) | gb else gb
            xa * xb
          case _ => ga * gb
        }) & mask)
        val res  = sext(mod.io.p.peek().litValue)
        val diff = res - prd
        if (results.contains(prd)) results(prd) += diff
        else results(prd) = mutable.ArrayBuffer(diff)
      }
    } else { // random run with fewer tests
      val nTests = getNTests(scala.math.max(mod.aWidth, mod.bWidth))
      for (_ <- 0 until nTests * nTests) {
        val a = BigInt(mod.aWidth, rng)
        mod.io.a.poke(a.U)
        val b = BigInt(mod.aWidth, rng)
        mod.io.b.poke(b.U)
        // Optionally sign-extend product and result and compute the difference
        val prd = sext((sgn match {
          case Signed =>
            val xa = if (a.testBit(mod.aWidth-1)) (BigInt(-1) << mod.aWidth) | a else a
            val xb = if (b.testBit(mod.bWidth-1)) (BigInt(-1) << mod.bWidth) | b else b
            xa * xb
          case _ => a * b
        }) & mask)
        val res  = sext(mod.io.p.peek().litValue)
        val diff = res - prd
        if (results.contains(prd)) results(prd) += diff
        else results(prd) = mutable.ArrayBuffer(diff)
      }
    }

    // Output results to a binary file
    _writeRand2D(results.map { case (pd, ls) => pd -> ls.toArray }.toMap, mod.aWidth, mod.bWidth)
    println(s"${_info} Wrote results to $path/errors.bin")
  }

  private[MultiplierCharacterizer] def _charRand3D[T <: Multiplier](mod: T): Unit = {
    assume(mod.aWidth <= 64 && mod.bWidth <= 64,
      "cannot randomly characterize multipliers with more than 64-bit inputs")
    assume(mod.aWidth == mod.bWidth, "cannot characterize multipliers with non-equal input bit-widths")
    val pWidth = mod.aWidth + mod.bWidth

    // Write something to the terminal
    println(s"${_info} $chartype $sgn multiplier characterization")

    /** Optionally sign-extend a result from the multiplier */
    def sext(num: BigInt): BigInt = sgn match {
      case Signed => if (num.testBit(pWidth-1)) (BigInt(-1) << pWidth) | num else num
      case _ => num
    }

    // Run through a load of random input combinations and store the
    // error results per domain
    val mask = ((BigInt(1) << pWidth) - 1)
    val rng  = new scala.util.Random(42)
    val results = mutable.Map.empty[(BigInt, BigInt), BigInt]
    if (mod.aWidth <= 10) { // exhaustive run
      for (a <- 0 until (1 << mod.aWidth); b <- 0 until (1 << mod.aWidth)) {
        mod.io.a.poke(a.U)
        mod.io.b.poke(b.U)
        // Optionally sign-extend product and result and compute the difference
        val (ga, gb) = (BigInt(a), BigInt(b))
        val prd = sext((sgn match {
          case Signed =>
            val xa = if (ga.testBit(mod.aWidth-1)) (BigInt(-1) << mod.aWidth) | ga else ga
            val xb = if (gb.testBit(mod.bWidth-1)) (BigInt(-1) << mod.bWidth) | gb else gb
            xa * xb
          case _ => ga * gb
        }) & mask)
        val res  = sext(mod.io.p.peek().litValue)
        val diff = res - prd
        results += ((ga, gb) -> diff)
      }
    } else { // random run with fewer tests
      val nTests = getNTests(scala.math.max(mod.aWidth, mod.bWidth))
      for (_ <- 0 until nTests * nTests) {
        val a = BigInt(mod.aWidth, rng)
        mod.io.a.poke(a.U)
        val b = BigInt(mod.aWidth, rng)
        mod.io.b.poke(b.U)
        // Optionally sign-extend product and result and compute the difference
        val prd = sext((sgn match {
          case Signed =>
            val xa = if (a.testBit(mod.aWidth-1)) (BigInt(-1) << mod.aWidth) | a else a
            val xb = if (b.testBit(mod.bWidth-1)) (BigInt(-1) << mod.bWidth) | b else b
            xa * xb
          case _ => a * b
        }) & mask)
        val res  = sext(mod.io.p.peek().litValue)
        val diff = res - prd
        results += ((a, b) -> diff)
      }
    }

    // Output results to a binary file
    _writeRand3D(results.toMap, mod.aWidth, mod.bWidth)
    println(s"${_info} Wrote results to $path/errors.bin")
  }
}
