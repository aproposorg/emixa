
package emixa
import Characterization._
import Signedness._

import chisel3._
import chiseltest._
import chisel3.util.log2Up

import scala.collection.mutable

import approx.addition.Adder

abstract class AdderCharacterizer extends Characterizer {
  private[emixa] def _characterize[T <: Module](mod: T): Unit = mod match {
    case adder: Adder =>
      chartype match {
        case Exhaustive => _charExhaustive(adder)
        case Random2D   => _charRand2D(adder)
        case Random3D   => _charRand3D(adder)
      }
    case other => throw new IllegalArgumentException(s"cannot characterize module $other")
  }

  private[AdderCharacterizer] def _charExhaustive[T <: Adder](mod: T): Unit = {
    assume(mod.width <= 10, "cannot exhaustively characterize adders with more than 10-bit inputs")

    // Write something to the terminal
    println(s"${_info} $chartype $sgn adder characterization")

    // Run through all input combinations and store the error distance results
    val mask = ((BigInt(1) << mod.width) - 1)
    mod.io.cin.poke(false.B)
    val results = (0 until (1 << mod.width)).flatMap { a =>
      mod.io.a.poke(a.U)
      (0 until (1 << mod.width)).map { b =>
        mod.io.b.poke(b.U)
        mod.io.s.peek().litValue - ((BigInt(a) + BigInt(b)) & mask)
      }
    }

    // Output results to a binary file
    _writeExhaustive(results.toArray, mod.width, mod.width)
    println(s"${_info} Wrote results to $path/errors.bin")
  }

  private[AdderCharacterizer] def _charRand2D[T <: Adder](mod: T): Unit = {
    assume(mod.width <= 64, "cannot randomly characterize adders with more than 64-bit inputs")

    // Write something to the terminal
    println(s"${_info} $chartype $sgn adder characterization")

    // Run through a load of random input combinations and store the
    // error results per result
    val mask = ((BigInt(1) << mod.width) - 1)
    val rng  = new scala.util.Random(42)
    mod.io.cin.poke(false.B)
    val results = mutable.Map.empty[BigInt, mutable.ArrayBuffer[BigInt]]
    if (mod.width <= 10) { // exhaustive run
      for (a <- 0 until (1 << mod.width); b <- 0 until (1 << mod.width)) {
        mod.io.a.poke(a.U)
        mod.io.b.poke(b.U)
        val sum = (BigInt(a) + BigInt(b)) & mask
        if (results.contains(sum)) results(sum) += (mod.io.s.peek().litValue - sum)
        else results(sum) = mutable.ArrayBuffer(mod.io.s.peek().litValue - sum)
      }
    } else { // random run with fewer tests
      val nTests = 1 << (scala.math.sqrt(mod.width) + 1).round.toInt
      for (_ <- 0 until nTests * nTests) {
        val a = BigInt(mod.width, rng)
        mod.io.a.poke(a.U)
        val b = BigInt(mod.width, rng)
        mod.io.b.poke(b.U)
        val sum = (a + b) & mask
        if (results.contains(sum)) results(sum) += (mod.io.s.peek().litValue - sum)
        else results(sum) = mutable.ArrayBuffer(mod.io.s.peek().litValue - sum)
      }
    }

    // Output results to a binary file
    _writeRand2D(results.map { case (s, ress) => s -> ress.sum.toDouble / ress.size }.toMap, mod.width, mod.width)
    println(s"${_info} Wrote results to $path/errors.bin")
  }

  private[AdderCharacterizer] def _charRand3D[T <: Adder](mod: T): Unit = {
    assume(mod.width <= 64, "cannot randomly characterize adders with more than 64-bit inputs")

    // Write something to the terminal
    println(s"${_info} $chartype $sgn adder characterization")

    // Run through a load of random input combinations and store the
    // error results per domain
    val mask = ((BigInt(1) << mod.width) - 1)
    val rng  = new scala.util.Random(42)
    mod.io.cin.poke(false.B)
    val results = mutable.Map.empty[(BigInt, BigInt), BigInt]
    if (mod.width <= 10) { // exhaustive run
      for (a <- 0 until (1 << mod.width); b <- 0 until (1 << mod.width)) {
        mod.io.a.poke(a.U)
        mod.io.b.poke(b.U)
        val sum = (BigInt(a) + BigInt(b)) & mask
        results += ((BigInt(a), BigInt(b)) -> (mod.io.s.peek().litValue - sum))
      }
    } else { // random run with fewer tests
      val nTests = 1 << (scala.math.sqrt(mod.width) + 1).round.toInt
      for (_ <- 0 until nTests * nTests) {
        val a = BigInt(mod.width, rng)
        mod.io.a.poke(a.U)
        val b = BigInt(mod.width, rng)
        mod.io.b.poke(b.U)
        val sum = (a + b) & mask
        results += ((a, b) -> (mod.io.s.peek().litValue - sum))
      }
    }

    // Output results to a binary file
    _writeRand3D(results.toMap, mod.width, mod.width)
    println(s"${_info} Wrote results to $path/errors.bin")
  }
}
