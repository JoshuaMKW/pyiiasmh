#  PyiiASMH (pyiiasmh_cli.py)
#  Copyright (c) 2011, 2012, Sean Power
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#      * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#      * Neither the names of the authors nor the
#        names of its contributors may be used to endorse or promote products
#        derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL SEAN POWER BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import shutil
import logging
import binascii
import tempfile

import ppctools
from errors import CodetypeError, UnsupportedOSError


class PyiiAsmhApp(object):

    def __init__(self):
        self.opcodes = None
        self.geckocodes = None
        self.bapo = None
        self.xor = None
        self.chksum = None
        self.codetype = None

        self.log = logging.getLogger("PyiiASMH")
        hdlr = logging.FileHandler("error.log")
        formatter = logging.Formatter(
            "\n%(levelname)s (%(asctime)s): %(message)s")
        hdlr.setFormatter(formatter)
        self.log.addHandler(hdlr)

    def assemble(self, inputfile, outputfile=None, filetype="text"):
        tmpdir = tempfile.mkdtemp(prefix="pyiiasmh-") + os.path.normcase("/")

        if filetype is None:
            try:
                f = open(tmpdir+"code.txt", "w")
            except IOError:
                self.log.exception("Failed to open input file.")
                shutil.rmtree(tmpdir)
                return None
            else:
                try:
                    f.seek(0)
                    f.write(inputfile)
                finally:
                    f.close()
                inputfile = None

        try:
            toReturn = ""
            geckocodes = ppctools.asm_opcodes(tmpdir, inputfile, outputfile)
        except UnsupportedOSError:
            self.log.exception()
            toReturn = ("Your OS '" + sys.platform + "' is not supported. " +
                        "See 'error.log' for details and also read the README.")
        except IOError as e:
            self.log.exception(e)
            toReturn = "Error: " + str(e)
        except RuntimeError as e:
            self.log.exception(e)
            toReturn = str(e)
        else:
            toReturn = ppctools.construct_code(geckocodes,
                                               self.bapo, self.xor, self.chksum, self.codetype)

        shutil.rmtree(tmpdir)
        return toReturn

    def disassemble(self, inputfile, outputfile=None, filetype="text"):
        tmpdir = tempfile.mkdtemp(prefix="pyiiasmh-") + os.path.normcase("/")
        codes = None

        if filetype is None:
            codes = inputfile
        else:
            try:
                if filetype == "bin":
                    f = open(inputfile, "rb")
                else:
                    f = open(inputfile, "r")
            except IOError:
                self.log.exception("Failed to open input file.")
                shutil.rmtree(tmpdir)
                return None
            else:
                try:
                    f.seek(0)
                    codes = "".join(f.readlines())
                    if filetype == "bin":
                        codes = binascii.b2a_hex("".join(codes)).upper()
                finally:
                    f.close()

        rawcodes = ppctools.deconstruct_code(codes)

        try:
            f = open(tmpdir+"code.bin", "wb")
        except IOError:
            self.log.exception("Failed to open temp file.")
        else:
            try:
                f.seek(0)
                rawhex = "".join("".join(rawcodes[0].split("\n")).split(" "))
                f.write(binascii.a2b_hex(rawhex))
            except IOError:
                self.log.exception("Failed to write input data to file.")
            except TypeError as e:
                self.log.exception(e)
            finally:
                f.close()

        try:
            toReturn = ("", (None, None, None, None))
            opcodes = ppctools.dsm_geckocodes(tmpdir, outputfile, None)
        except UnsupportedOSError:
            self.log.exception("")
            toReturn = (("Your OS '" + sys.platform + "' is not supported. " +
                         "See 'error.log' for details and also read the README."),
                        (None, None, None, None))
        except IOError as e:
            self.log.exception(e)
            toReturn = ("Error: " + str(e), (None, None, None, None))
        except RuntimeError as e:
            self.log.exception(e)
            toReturn = (str(e), (None, None, None, None))
        else:
            toReturn = (opcodes + "\n", rawcodes[1:])

        shutil.rmtree(tmpdir)
        return toReturn

    def print_usage(self, err=None):
        if err:
            print(err+"\n")
        name = "PyiiASMH-cli"

        print("Usage: " + name + " <command> <options> <input_file> "
              + "[<output_file>]")
        print("  or:  " + name + " <command> <options> <input_file> "
              + "[<output_file>]")
        print("")
        print("Commands:")
        print("    -a, --asm, --assemble\tAssemble ppc opcodes to gecko codes")
        print("    -d, --dsm, --disassemble\tDisassemble gecko codes to ppc opcodes")
        print("    -h, --help           \tView this info")
        print("")
        print("Options:")
        print("    -codetype CODETYPE\tThis must come before other options.")
        print("                      \t  Codetypes: \"C0\", \"C2D2\", \"F2F4\"")
        print("")
        print("Options (for -a, --asm, --assemble):")
        print("    -bapo ADDRESS\tThis is expected next if \"C2D2\" or \"F2F4\" is")
        print("                 \t  is given for a codetype.")
        print("    -xor VALUE   \tThis is expected if \"F2F4\" is the codetype.")
        print("    -chksum VALUE\tThis is expected if \"F2F4\" is the codetype.")
        print("")
        print("Options (for -d, --dsm, --disassemble):")
        print("    -filetype TYPE\tType of the input file to use.")
        print("                  \t  Filetypes: \"text\" (default), \"bin\"")
        print("")
        print("Examples:")
        print("    "+name+" -a -codetype C0 code.txt out.bin")
        print("    "+name+" -a -codetype C2D2 -bapo 80DEAD00 code.txt")
        print("    "+name+" -d input.txt")
        print("    "+name+" -d -filetype bin input.bin out.txt")
        print("")
        print("By default, output will be printed as text to stdout. A file")
        print("can be specified as an agrument to change this behavior.")
        print("Output files will be binary when assembling and text when")
        print("disassembling. Read the README for more details.")
        sys.exit(1)

    def run(self, args):
        commands = ("-a", "-d", "-h", "--asm", "--dsm",
                    "--assemble", "--disassemble", "--help")
        options = ("-filetype", "-codetype", "-bapo", ("-xor", "-chksum"))
        filetypes = ("text", "bin")
        codetypes = ("C0", "C2D2", "F2F4", "RAW")
        good_bapo = ("80", "81", "00", "01")
        inputfile_argnum = 1
        filetype = "text"

        try:
            # Check for incorrect usage
            if args[0] not in commands:
                self.print_usage("Invalid command '"+args[0]+"'")
            elif args[0] in ("-h", "--help"):
                self.print_usage()

            elif args[1] != "-codetype":
                if args[1] == "-filetype":
                    if args[2] not in filetypes:
                        self.print_usage("'"+args[2]+"' is invalid filetype")

                    filetype = args[2]
                    inputfile_argnum = 3
                    open(args[3], "r").close()
                else:
                    open(args[1], "r").close()

            elif args[2].upper() not in codetypes:
                self.print_usage("Invalid codetype '"+args[2]+"'")
            elif args[2].upper() == "RAW":
                open(args[1], "r").close()
            else:
                self.codetype = args[2].upper()
                if self.codetype == "C0":
                    inputfile_argnum = 3
                    open(args[3], "r").close()

                elif args[3] != "-bapo":
                    self.print_usage("Bad option order; "
                                     + "expected '-bapo'")
                elif len(args[4]) != 8 or args[4][:2] not in good_bapo:
                    self.print_usage("'"+args[4]+"' not valid")
                elif self.codetype == "C2D2":
                    int(args[4], 16)
                    self.bapo = args[4]
                    inputfile_argnum = 5
                    open(args[5], "r").close()
                # F2F4
                elif args[5] not in options[3] or args[7] not in options[3]:
                    self.print_usage("Error: expected '-xor' or '-chksum'"
                                     + " ('"+args[5]+"', '"+args[7]+"')")
                elif args[5] == args[7]:
                    self.print_usage("Error: duplicate arguments")
                else:
                    xornum = 5
                    chknum = 7
                    int(args[4], 16)
                    self.bapo = args[4]

                    if args[7] == "-xor":
                        xornum = 7
                        chknum = 5

                    if len(args[xornum+1]) != 4:
                        self.print_usage("'"+args[xornum+1]+"' not valid")
                    elif len(args[chknum+1]) != 2:
                        self.print_usage("'"+args[chknum+1]+"' not valid")

                    int(args[6], 16)
                    int(args[8], 16)
                    self.xor = args[xornum+1]
                    self.chksum = args[chknum+1]
                    inputfile_argnum = 9
                    open(args[9], "r").close()
        except IndexError:
            self.print_usage()
        except ValueError:
            self.print_usage("Invalid hex value")
        except IOError:
            self.print_usage(
                "Input file '"+args[inputfile_argnum]+"' not found")
        else:
            try:  # See if user gave output file
                args[inputfile_argnum+1]
            except IndexError:  # no output file, print(to stdout
                if args[0] in ("-a", "--assemble"):
                    print(self.assemble(args[inputfile_argnum], None,
                                        filetype))
                else:
                    print(self.disassemble(args[inputfile_argnum], None,
                                           filetype)[0])
            else:  # output file specified
                if args[0] in ("-a", "--assemble"):
                    self.assemble(args[inputfile_argnum],
                                  args[inputfile_argnum+1], filetype)
                else:
                    self.disassemble(args[inputfile_argnum],
                                     args[inputfile_argnum+1], filetype)


if __name__ == "__main__":
    app = PyiiAsmhApp()
    app.run(sys.argv[1:])
