#!/usr/bin/env python3

#  PyiiASMH 3 (pyiiasmh_cli.py)
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

import binascii
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from argparse import ArgumentParser

import ppctools
from errors import CodetypeError, UnsupportedOSError

def resource_path(relative_path: str = "") -> str:
    """ Get absolute path to resource, works for dev and for cx_freeze """
    if getattr(sys, "frozen", False):
        # The application is frozen
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(base_path, relative_path)

class PyiiAsmhApp(object):

    def __init__(self):
        os.chdir(resource_path())
        
        self.opcodes = None
        self.geckocodes = None
        self.bapo = None
        self.xor = None
        self.chksum = None
        self.codetype = None

        self.log = logging.getLogger("PyiiASMH")
        hdlr = logging.FileHandler("error.log")
        formatter = logging.Formatter("\n%(levelname)s (%(asctime)s): %(message)s")
        hdlr.setFormatter(formatter)
        self.log.addHandler(hdlr)

    def assemble(self, inputfile, outputfile=None, filetype="text"):
        tmpdir = tempfile.mkdtemp(prefix="pyiiasmh-")

        if filetype is None:
            try:
                with open(os.path.join(tmpdir, "code.txt"), "w") as f:
                    f.write(inputfile)
                inputfile = None
            except IOError:
                self.log.exception("Failed to open input file.")
                shutil.rmtree(tmpdir)
                return None

        try:
            toReturn = ""
            machine_code = ppctools.asm_opcodes(tmpdir, inputfile)
        except UnsupportedOSError as e:
            self.log.exception(e)
            toReturn = (f"Your OS '{sys.platform}' is not supported. See 'error.log' for details and also read the README.")
        except IOError as e:
            self.log.exception(e)
            toReturn = f"Error: {str(e)}"
        except RuntimeError as e:
            self.log.exception(e)
            toReturn = str(e)
        else:
            if self.bapo is not None:
                if self.bapo[0] not in ("8", "0") or self.bapo[1] not in ("0", "1"):
                    return f"Invalid ba/po: {self.bapo}"
                elif int(self.bapo[2], 16) > 7 and self.bapo[1] == '1':
                    return f"Invalid ba/po: {self.bapo}"

            toReturn = ppctools.construct_code(machine_code, self.bapo, self.xor, self.chksum, self.codetype)
            if outputfile is not None:
                if filetype == 'text':
                    with open(outputfile, 'w+') as output:
                        output.write(toReturn)
                elif filetype == 'bin':
                    with open(outputfile, 'wb+') as output:
                        output.write(bytes.fromhex(toReturn.replace('\n', '').replace(' ', '')))
                else:
                    with open(outputfile, 'w+') as output:
                        output.write(toReturn)
        
        shutil.rmtree(tmpdir, ignore_errors=True)
        return toReturn

    def disassemble(self, inputfile, outputfile=None, filetype="text", cFooter=True, formalNames=False):
        tmpdir = tempfile.mkdtemp(prefix="pyiiasmh-")
        codes = None

        if filetype == "bin":
            access = "rb"
        else:
            access = "r"

        if filetype is None:
            codes = inputfile
        else:
            try:
                with open(inputfile, access) as f:
                    codes = "".join(f.readlines())
                    if filetype == "bin":
                        codes = binascii.b2a_hex(codes).upper()
            except IOError as e:
                self.log.exception("Failed to open input file.")
                shutil.rmtree(tmpdir)
                return [f"Error: {str(e)}", (None, None, None, None)]

        rawcodes = ppctools.deconstruct_code(codes, cFooter)

        try:
            with open(os.path.join(tmpdir, "code.bin"), "wb") as f:
                rawhex = "".join("".join(rawcodes[0].split("\n")).split(" "))
                try:
                    f.write(binascii.a2b_hex(rawhex))
                except binascii.Error:
                    f.write(b"")
        except IOError:
            self.log.exception("Failed to open temp file.")

        try:
            toReturn = ["", (None, None, None, None)]
            opcodes = ppctools.dsm_geckocodes(tmpdir, outputfile)
        except UnsupportedOSError:
            self.log.exception("")
            toReturn = ((f"Your OS '{sys.platform}' is not supported. " +
                         "See 'error.log' for details and also read the README."),
                        (None, None, None, None))
        except IOError as e:
            self.log.exception(e)
            toReturn = ("Error: " + str(e), (None, None, None, None))
        except RuntimeError as e:
            self.log.exception(e)
            toReturn = (str(e), (None, None, None, None))
        else:
            toReturn = [opcodes + "\n", rawcodes[1:]]

        if formalNames:
            opcodes = []
            for line in toReturn[0].split("\n"):
                values = re.sub(r"(?<!c)r1(?![0-9])", "sp", line)
                values = re.sub(r"(?<!c)r2(?![0-9])", "rtoc", values)
                opcodes.append(values)
            toReturn[0] = "\n".join(opcodes)

        shutil.rmtree(tmpdir)

        return toReturn

    def run(self, parser, args, filetype='text'):
        # Check for incorrect usage
        if args.codetype.upper() == 'RAW':
            self.codetype = None
        else:
            self.codetype = args.codetype.upper()

        self.bapo = args.bapo
        self.xor = args.xor
        self.chksum = args.samples

        if args.assemble:
            if args.dest:
                self.assemble(args.source, args.dest, filetype=filetype)
            else:
                print('\n-----------------\n' + self.assemble(args.source, None, filetype=filetype).strip() + '\n-----------------\n')
        elif args.disassemble:
            if args.dest:
                self.disassemble(args.source, args.dest, filetype=filetype, cFooter=args.rmfooterasm, formalNames=args.formalnames)
            else:
                print('\n-----------------\n' + self.disassemble(args.source, None, filetype=filetype, cFooter=args.rmfooterasm, formalNames=args.formalnames)[0].strip() + '\n-----------------\n')
        else:
            parser.print_help()

def _ppc_exec():
    parser = ArgumentParser(prog='PyiiASMH 3',
                            description='Gecko code compiler for PPC assembly',
                            allow_abbrev=False)

    parser.add_argument('source', help='Source file')
    parser.add_argument('-a', '--assemble',
                        help='Assemble the target PPC assembly code into machine code',
                        action='store_true')
    parser.add_argument('-d', '--disassemble',
                        help='Disassemble the target machine code into PPC assembly',
                        action='store_true')
    parser.add_argument('--dest',
                        help='Destination file',
                        metavar='FILE')
    parser.add_argument('--bapo',
                        help='Address for the codehook',
                        default='80000000',
                        metavar='ADDR')
    parser.add_argument('--codetype',
                        help='The codetype being assembled',
                        choices=['0414', '0616', 'C0', 'C2D2', 'F2F4', 'RAW'],
                        default='RAW',
                        metavar='TYPE')
    parser.add_argument('--xor',
                        help='The XOR checksum in hex used for the F2/F4 codetype',
                        default='0000',
                        metavar='HEXVALUE')
    parser.add_argument('--samples',
                        help='''The number of samples in hex to be XORed for the F2/F4 codetype.
                        If negative, it searches backwards, else forwards''',
                        default='00',
                        metavar='HEXCOUNT')
    parser.add_argument('--formalnames',
                        help='Names r1 and r2 to be sp and rtoc respectively',
                        action='store_true')
    parser.add_argument('--rmfooterasm',
                        help='Removes the footer from a C0 block if possible, only useful if your code already contains an exit point',
                        action='store_true')

    args = parser.parse_args()
    dumptype = 'text'

    if args.bapo:
        try:
            addr = int(args.bapo, 16)
            if (addr < 0x80000000 or addr >= 0x81800000) and (addr < 0 or addr >= 0x01800000):
                parser.error('The given ba/po address value {} is invalid'.format(args.bapo))
        except ValueError:
            parser.error('The given ba/po address value {} is not a hex value'.format(args.bapo))
    
    if args.xor:
        try:
            int(args.xor, 16)
        except ValueError:
            parser.error('The given XOR value {} is not a hex value'.format(args.xor))
        if len(args.xor) > 4:
            parser.error('The given XOR value {} is too large'.format(args.xor))

    if args.samples:
        try:
            int(args.samples, 16)
        except ValueError:
            parser.error('The given samples value {} is not a hex value'.format(args.samples))
        if len(args.samples) > 2:
            parser.error('The given samples value {} is too large'.format(args.samples))

    if args.dest and args.assemble:
        if os.path.splitext(args.dest)[1].lower() == '.txt':
            dumptype = 'text'
        elif os.path.splitext(args.dest)[1].lower() in ('.bin', '.gct'):
            dumptype = 'bin'
        else:
            parser.error('Destination file {} is invalid type'.format(args.dest))
    elif args.dest and args.disassemble:
        if os.path.splitext(args.dest)[1].lower() != '.txt':
            parser.error('Destination file {} is invalid type'.format(args.dest))

    app = PyiiAsmhApp()
    app.run(parser, args, dumptype)

if __name__ == "__main__":
    _ppc_exec()
