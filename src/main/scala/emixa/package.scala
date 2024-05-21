
import chisel3._
import chiseltest.{ChiselScalatestTester, VerilatorBackendAnnotation, WriteVcdAnnotation}
import org.scalatest.flatspec.AnyFlatSpec

import java.io.{DataOutputStream, FileOutputStream, File}

import sys.process._

import scala.io.AnsiColor.{YELLOW, RED, RESET}

import scala.reflect.ClassTag
import scala.reflect.runtime.{currentMirror => cm, universe => ru}

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
   * primary constructor
   */
  private[emixa] def info[T : ru.TypeTag] = {
    val ctor = ru.typeOf[T].decl(ru.termNames.CONSTRUCTOR).asMethod
    val allAddDefs = ctor.paramLists.drop(1).flatten.forall(_.asTerm.isParamWithDefault)
    if (ctor.paramLists.size > 1 && !allAddDefs) {
      print(s"${_error} Cannot runtime instantiate classes with multiple parameter ")
      println("lists without default arguments in all additional parameter lists")
      throw new IllegalArgumentException("multiple parameter lists")
    }
    val args = ctor.paramLists.head.map(param => (param.name.toString, param.info))
    args
  }

  /** Get a map of optional default parameters for a runtime class'
   * primary constructor
   */
  def defParamMap[T : ru.TypeTag]: Map[Int, Option[Any]] = {
    // Extract the primary constructor and use its parameter list 
    // for constructing the resulting map
    val primCtor = ru.typeOf[T]
      .decl(ru.termNames.CONSTRUCTOR)
      .asMethod
    val allAddDefs = primCtor.paramLists
      .drop(1)
      .flatten
      .forall(_.asTerm.isParamWithDefault)
    if (primCtor.paramLists.size > 1 && !allAddDefs) {
      print(s"[ERROR] Cannot runtime instantiate classes with multiple parameter ")
      println("lists without default arguments in all additional parameter lists")
      throw new IllegalArgumentException("multiple parameter lists")
    }

    // If the constructor has no default parameters, do not attempt 
    // to find its companion object
    if (!primCtor.paramLists.head.exists(_.asTerm.isParamWithDefault)) {
      (0 until primCtor.paramLists.head.size).map(_ -> None).toMap
    } else {
      // Get the companion object, which houses the default value methods
      val clsCompMod = ru.typeOf[T]
        .typeSymbol
        .asClass
        .companion
        .asModule
      val instMirr = cm.reflectModule(clsCompMod).instance

      // Use the primary constructor's parameter list for building the map
      primCtor.paramLists.head.zipWithIndex.map { case (param, ind) =>
        // If the parameter has no default value, no need to search for 
        // its default value method
        if (!param.asTerm.isParamWithDefault) {
          (ind -> None)
        } else {
          val mthd = clsCompMod.typeSignature
            .member(ru.TermName(s"$$lessinit$$greater$$default$$${ind+1}"))
            .asMethod
          val prm = cm.reflect(instMirr).reflectMethod(mthd)()
          (ind -> Some(prm))
        }
      }.toMap
    }
  }

  /** Produce a helper string about a runtime class' primary constructor */
  private[emixa] def help[T : ru.TypeTag] = {
    // Gather some information about the constructur
    val const  = info[T]
    val params = defParamMap[T]
    val name   = ru.typeOf[T].toString.split('.').last
    val llen   = const.map(_._1.size).max

    // Now build the resulting string
    val bs = new StringBuilder(s"${_info} $name takes ${const.size} arguments:")
    const.zipWithIndex.foreach { case ((nme, tpe), ind) =>
      val default = params(ind) match {
        case Some(value) => s"(defaults to $value)"
        case _ => ""
      }
      bs.append(s"\n${_info} - ${nme.padTo(llen, ' ')} : $tpe $default")
    }
    bs.mkString
  }

  /** Parse a map of named arguments into the type specified
   * by a runtime class' primary constructor
   */
  private[emixa] def parseArgMap[T : ru.TypeTag](args: Map[String, String]) = {
    val const = info[T]

    // Build a complete map of arguments, giving precedence to those passed 
    // via the command line
    val params = {
      val defArgs = defParamMap[T]
      val nmdDefArgs = const.zipWithIndex
        .map { case ((nme, _), ind) =>
          defArgs(ind) match {
            case Some(value) => (nme -> Some(value.toString()))
            case _ => (nme -> None)
          }
        }.toMap
      nmdDefArgs ++ args.map { case (k, v) => (k -> Some(v)) }
    }

    // Ensure these arguments cover the constructor
    if (params.filter(_._2 == None).nonEmpty) {
      val name = ru.typeOf[T].toString.split('.').last
      val llen = const.map(_._1.size).max
      val bs = new StringBuilder(s"${_error} Missing arguments for $name:")
      const.foreach { case (nme, tpe) =>
        val arg = params(nme) match {
          case Some(value) => s"(got $value)"
          case _ => "(missing)"
        }
        bs.append(s"\n${_error} - ${nme.padTo(llen, ' ')} : $tpe $arg")
      }
      println(bs.mkString)
      throw new IllegalArgumentException("arguments missing for test")
    }

    // Convert and package the arguments properly
    const.map { case (nme, tpe) =>
      val arg  = params(nme).get // safe since check above passed
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
          println(s"${_error} Cannot parse argument \"$nme=$arg\" into type $tpe. Use:")
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

  /** Compute the number of random tests to execute for a module
   * @param width the width of the module operands
   * @return a number of tests
   */
  private[emixa] def getNTests(width: Int): Int = {
    require(width >= 0)
    1 << (1.25 * scala.math.sqrt(width) + 1).round.toInt
  }

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
    private[emixa] val symAnnos = if ("which verilator".! == 0) Seq(VerilatorBackendAnnotation, WriteVcdAnnotation) else Seq(WriteVcdAnnotation)

    /** Create folders to result file path */
    (new File(path)).mkdirs()
    // Files.createDirectories(Paths.get(path))

    /** Some tricky overriding to get access to the config map via
     * the ChiselScalatestTester trait
     */
    private[emixa] var cmdArgMap = Map.empty[String, String]
    private[emixa] var context = new scala.util.DynamicVariable[Option[NoArgTest]](None)
    override def withFixture(test: NoArgTest): org.scalatest.Outcome = {
      require(context.value.isEmpty)
      context.withValue(Some(test)) {
        cmdArgMap = test.configMap.map { case (k, v) => k -> v.toString() }
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
        test(instantiate(ct.runtimeClass)(parseArgMap[T](cmdArgMap):_*).asInstanceOf[T])
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
      os.close()
    }

    /** Write the results of a random 2D characterization to a binary file
     * @param results a map of results from the characterization
     * @param params any number of integral parameters to output
     */
    private[emixa] def _writeRand2D(results: Map[BigInt, Array[BigInt]], params: Int*): Unit = {
      val os = new DataOutputStream(new FileOutputStream(new File(s"$path/errors.bin")))
      params.foreach(param => os.writeInt(param))
      results.foreach { case (sm, ls) =>
        os.writeLong(sm.longValue)
        os.writeInt(ls.size)
        ls.foreach(rs => os.writeLong(rs.longValue))
      }
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
      os.close()
    }
  }
}
