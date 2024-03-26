
import chisel3._
import chiseltest.{ChiselScalatestTester, VerilatorBackendAnnotation}
import org.scalatest.flatspec.AnyFlatSpec

import java.io.{DataOutputStream, FileOutputStream, File}
import java.nio.file.{Files, Paths}

import sys.process._

import scala.io.AnsiColor.{YELLOW, RED, RESET}
import scala.util.{Either, Left, Right}

import scala.reflect.ClassTag
import scala.reflect.runtime.{universe => ru}

/** Common, reusable test patterns for error characterization of inexact
 * adders and multipliers within the emixa framework
 */
package object emixa {

  /** Default path to result files */
  private[emixa] val ResultPath = "./output/"

  /** Colored error labels */
  private[emixa] val _info    =  "[emixa-info]"
  private[emixa] val _warning = s"[${YELLOW}emixa-warning${RESET}]"
  private[emixa] val _error   = s"[${RED}emixa-error${RESET}]"

  /** Get the type tag of a runtime class by reflection */
  private[emixa] def getTypeTag[T](implicit tt: ru.TypeTag[T]) = tt

  /** Get the name and type information about a runtime class'
   * first constructor
   */
  private[emixa] def info[T : ru.TypeTag] = {
    val cstctr = ru.typeOf[T].decl(ru.termNames.CONSTRUCTOR).asMethod
    val args = cstctr.paramLists.head.map(param => (param.name.toString, param.info))
    args
  }

  /** Produce a helper string about a runtime class' first
   * constructor
   */
  private[emixa] def help[T : ru.TypeTag] = {
    val const = info[T]
    val name  = ru.typeOf[T].toString.split('.').last
    val llen  = const.map(_._1.size).max
    val res = s"""${_info} ${name} takes ${const.size} arguments:
                 |${const.map { case (nme, tpe) => s"${_info} - ${nme.padTo(llen, ' ')} : $tpe" }.mkString("\n")}""".stripMargin
    res
  }

  /** Parse a string of whitespace-separated arguments into
   * the type specified by a runtime class' first constructor
   */
  private[emixa] def parseArgs[T : ru.TypeTag](args: String) = {
    val const = info[T]
    val split = args.split(' ')
    if (split.size < const.size) {
      val name = ru.typeOf[T].toString.split('.').last
      println(s"${_error} Missing arguments for constructor of ${name}: Expected ${const.size}, got ${split.size}. Use:")
      println(help[T])
      throw new IllegalArgumentException("arguments missing for test")
    }
    const.zip(split).map { case ((nme, tpe), arg) =>
      val conv = tpe match {
        case bte  if bte  =:= ru.typeOf[Byte]    => arg.toByteOption.map(Byte.box(_))
        case shrt if shrt =:= ru.typeOf[Short]   => arg.toShortOption.map(Short.box(_))
        case int  if int  =:= ru.typeOf[Int]     => arg.toIntOption.map(Int.box(_))
        case lng  if lng  =:= ru.typeOf[Long]    => arg.toLongOption.map(Long.box(_))
        case bool if bool =:= ru.typeOf[Boolean] => arg.toBooleanOption.map(Boolean.box(_))
        case flt  if flt  =:= ru.typeOf[Float]   => arg.toFloatOption.map(Float.box(_))
        case dbl  if dbl  =:= ru.typeOf[Double]  => arg.toDoubleOption.map(Double.box(_))
        case chr  if chr  =:= ru.typeOf[Char]    => arg.headOption.map(Char.box(_))
        case str  if str  =:= ru.typeOf[String]  => Some(arg)
        case _ => None
      }
      conv match {
        case None =>
          println(s"${_error} Cannot parse argument \"$arg\" into type $tpe. Use:")
          println(help[T])
          throw new IllegalArgumentException("invalid argument passed to test")
        case _ => conv.get
      }
    }
  }

  /** Instantiate an object of a runtime class with reflection */
  private[emixa] def instantiate[T](clazz: java.lang.Class[T])(args: AnyRef*): T = {
    return clazz.getConstructors().head.newInstance(args:_*).asInstanceOf[T]
  }

  /** 
   * The EMIXA library components
   */

  /** Signedness of the inexact arithmetic unit to characterize */
  object Signedness extends Enumeration {
    type Signedness = Value

    val Unsigned = Value("unsigned")
    val Signed   = Value("signed")
  }
  import Signedness._

  /** Style of characterization to perform
   * 
   * Users have an option of 
   */
  object Characterization extends Enumeration {
    type Characterization = Value

    val Exhaustive = Value("Exhaustive")
    val Random2D   = Value("Random2D")
    val Random3D   = Value("Random3D")
  }
  import Characterization._

  /** Generic characterizer interface that serves as foundation for
   * any characterizer for a particular type of arithmetic unit
   * 
   * @note Inheriting classes must define two parameters `sgn` and
   *       `chartype`, describing the signedness of the arithmetic
   *       unit undergoing characterization and the type of
   *       characterization to perform.
   * 
   * @note Permits passing command line arguments to a test but
   *       ignores any names they are assigned to (for now).
   */
  private[emixa] abstract class Characterizer extends AnyFlatSpec with ChiselScalatestTester {
    this: org.scalatest.TestSuite =>

    def sgn: Signedness
    def chartype: Characterization

    /** Path to result files */
    private[emixa] val path = s"$ResultPath${this.getClass.getSimpleName}"

    /** Check if Verilator is available for simulations */
    private[emixa] val symAnnos = if ("which verilator".! == 0) Seq(VerilatorBackendAnnotation) else Seq()

    /** Create folders to result file path */
    Files.createDirectories(Paths.get(path))

    /** Some tricky overriding to get access to the config map via
     * the ChiselScalatestTester trait
     */
    private[emixa] var cmdArgs: String = ""
    private[emixa] var context = new scala.util.DynamicVariable[Option[NoArgTest]](None)
    override def withFixture(test: NoArgTest): org.scalatest.Outcome = {
      require(context.value.isEmpty)
      context.withValue(Some(test)) {
        cmdArgs = test.configMap.map(_._2).mkString(" ")
        super.withFixture(test)
      }
    }

    /** Empty function template for characterization
     * @param mod the inexact arithmetic unit to characterize
     */
    private[emixa] def _characterize[T <: Module](mod: T): Unit

    /** Function that all inheriting classes should call to perform
     * any characterization
     */
    def characterize[T <: Module]()(implicit ct: ClassTag[T], tt: ru.TypeTag[T]): Unit = {
      ct.runtimeClass.getSimpleName() should "characterize" in {
        test(instantiate(ct.runtimeClass)(parseArgs[T](cmdArgs):_*).asInstanceOf[T])
          .withAnnotations(symAnnos) { dut => _characterize(dut) }
      }
    }

    /** Write the results of an exhaustive characterization to a binary file
     * @param results an array of results from the characterization
     * @param params any number of integral parameters to output
     */
    private[emixa] def _writeExhaustive(results: Array[BigInt], params: Int*): Unit = {
      val os = new DataOutputStream(new FileOutputStream(new File(s"$path/errors.bin")))
      params.foreach(param => os.writeInt(param))
      results.foreach(res => os.writeLong(res.longValue))
      os.flush()
      os.close()
    }

    /** Write the results of a random 2D characterization to a binary file
     * @param results a map of results from the characterization
     * @param params any number of integral parameters to output
     */
    private[emixa] def _writeRand2D(results: Map[BigInt, Double], params: Int*): Unit = {
      val os = new DataOutputStream(new FileOutputStream(new File(s"$path/errors.bin")))
      params.foreach(param => os.writeInt(param))
      results.foreach { case (sum, res) =>
        os.writeLong(sum.longValue)
        os.writeDouble(res)
      }
      os.flush()
      os.close()
    }

    /** Write the results of a random 3D characterization to a binary file
     * @param results a map of results from the characterization
     * @param params any number of integral parameters to output
     */
    private[emixa] def _writeRand3D(results: Map[(BigInt, BigInt), BigInt], params: Int*): Unit = {
      val os = new DataOutputStream(new FileOutputStream(new File(s"$path/errors.bin")))
      params.foreach(param => os.writeInt(param))
      results.foreach { case ((a, b), res) =>
        os.writeLong(a.longValue)
        os.writeLong(b.longValue)
        os.writeLong(res.longValue)
      }
      os.flush()
      os.close()
    }
  }
}
