
package emixa
import Characterization._

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

    // Write something to the terminal
    println(s"${_info} $chartype $sgn multiplier characterization")

    // Run through all input combinations and store the error distance results
    val mask = ((BigInt(1) << mod.aWidth) - 1)
    val results = (0 until (1 << mod.aWidth)).flatMap { a =>
      mod.io.a.poke(a.U)
      (0 until (1 << mod.aWidth)).map { b =>
        mod.io.b.poke(b.U)
        (mod.io.p.peek().litValue & mask) - ((BigInt(a) * BigInt(b)) & mask)
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

    // Write something to the terminal
    println(s"${_info} $chartype $sgn multiplier characterization")

    // Run through a load of random input combinations and store the
    // error results per result
    val mask = ((BigInt(1) << mod.aWidth) - 1)
    val rng  = new scala.util.Random(42)
    val results = mutable.Map.empty[BigInt, mutable.ArrayBuffer[BigInt]]
    if (mod.aWidth <= 10) { // exhaustive run
      for (a <- 0 until (1 << mod.aWidth); b <- 0 until (1 << mod.aWidth)) {
        mod.io.a.poke(a.U)
        mod.io.b.poke(b.U)
        val prod = (BigInt(a) * BigInt(b)) & mask
        if (results.contains(prod)) results(prod) += ((mod.io.p.peek().litValue & mask) - prod)
        else results(prod) = mutable.ArrayBuffer((mod.io.p.peek().litValue & mask) - prod)
      }
    } else { // random run with fewer tests
      val nTests = 1 << (scala.math.sqrt(mod.aWidth) + 1).round.toInt
      for (_ <- 0 until nTests * nTests) {
        val a = BigInt(mod.aWidth, rng)
        mod.io.a.poke(a.U)
        val b = BigInt(mod.aWidth, rng)
        mod.io.b.poke(b.U)
        val prod = (a * b) & mask
        if (results.contains(prod)) results(prod) += ((mod.io.p.peek().litValue & mask) - prod)
        else results(prod) = mutable.ArrayBuffer((mod.io.p.peek().litValue & mask) - prod)
      }
    }

    // Output results to a binary file
    _writeRand2D(results.map { case (p, ress) => p -> ress.sum.toDouble / ress.size }.toMap, mod.aWidth, mod.bWidth)
    println(s"${_info} Wrote results to $path/errors.bin")
  }

  private[MultiplierCharacterizer] def _charRand3D[T <: Multiplier](mod: T): Unit = {
    assume(mod.aWidth <= 64 && mod.bWidth <= 64,
      "cannot randomly characterize multipliers with more than 64-bit inputs")
    assume(mod.aWidth == mod.bWidth, "cannot characterize multipliers with non-equal input bit-widths")

    // Write something to the terminal
    println(s"${_info} $chartype $sgn multiplier characterization")

    // Run through a load of random input combinations and store the
    // error results per domain
    val mask = ((BigInt(1) << mod.aWidth) - 1)
    val rng  = new scala.util.Random(42)
    val results = mutable.Map.empty[(BigInt, BigInt), BigInt]
    if (mod.aWidth <= 10) { // exhaustive run
      for (a <- 0 until (1 << mod.aWidth); b <- 0 until (1 << mod.aWidth)) {
        mod.io.a.poke(a.U)
        mod.io.b.poke(b.U)
        val prod = (BigInt(a) * BigInt(b)) & mask
        results += ((BigInt(a), BigInt(b)) -> ((mod.io.p.peek().litValue & mask) - prod))
      }
    } else { // random run with fewer tests
      val nTests = 1 << (scala.math.sqrt(mod.aWidth) + 1).round.toInt
      for (_ <- 0 until nTests * nTests) {
        val a = BigInt(mod.aWidth, rng)
        mod.io.a.poke(a.U)
        val b = BigInt(mod.aWidth, rng)
        mod.io.b.poke(b.U)
        val prod = (a * b) & mask
        results += ((a, b) -> ((mod.io.p.peek().litValue & mask) - prod))
      }
    }

    // Output results to a binary file
    _writeRand3D(results.toMap, mod.aWidth, mod.bWidth)
    println(s"${_info} Wrote results to $path/errors.bin")
  }
}
