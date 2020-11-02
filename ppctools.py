#  PyiiASMH (ppctools.py)
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
import re
import sys
import logging
import subprocess

from struct import calcsize
from errors import CodetypeError, UnsupportedOSError

def enclose_string(string: str) -> str:
    return "-"*(len(string) + 2) + "\n|" + string + "|\n" + "-"*(len(string) + 2)

def resource_path(relative_path: str = "") -> str:
    """ Get absolute path to resource, works for dev and for cx_freeze """
    if getattr(sys, "frozen", False):
        # The application is frozen
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(base_path, relative_path)

def get_program_folder(folder: str = "") -> str:
    """ Get path to appdata """
    if sys.platform == "win32":
        datapath = os.path.join(os.getenv("APPDATA"), folder)
    elif sys.platform == "darwin":
        if folder:
            folder = "." + folder
        datapath = os.path.join(os.path.expanduser("~"), "Library", "Application Support", folder)
    elif sys.platform == "linux":
        if folder:
            folder = "." + folder
        datapath = os.path.join(os.getenv("HOME"), folder)
    else:
        raise UnsupportedOSError(f"{sys.platform} OS is unsupported")
    return datapath

class PpcFormatter(object):
    AVAILABLE_PLATFORMS = ("darwin", "linux", "win32")

    def __init__(self):
        if not os.path.exists(get_program_folder("PyiiASMH-3")):
            os.mkdir(get_program_folder("PyiiASMH-3"))

        self.eabi = None
        self.vdappc = None

        self.log = logging.getLogger("PyiiASMH")
        hdlr = logging.FileHandler(os.path.join(get_program_folder("PyiiASMH-3"), "error.log"))
        formatter = logging.Formatter("\n%(levelname)s (%(asctime)s): %(message)s")
        hdlr.setFormatter(formatter)
        self.log.addHandler(hdlr)

        self._init_lib()

    def _init_lib(self):
        eabi = {}
        vdappc = ""

        # Pathnames for powerpc-eabi executables
        for i in ("as", "ld", "objcopy"):
            eabi[i] = resource_path(os.path.join("lib/", sys.platform))

            if sys.platform == "linux":
                if calcsize("P") * 8 == 64:
                    eabi[i] += "_x86_64"
                else:
                    eabi[i] += "_i686"

            eabi[i] += "/powerpc-eabi-" + i

            if sys.platform == "win32":
                eabi[i] += ".exe"

            eabi[i] = os.path.normpath(eabi[i])

        # Pathname for vdappc executable
        vdappc = resource_path(os.path.join("lib/", sys.platform))

        if sys.platform == "linux":
            if calcsize("P") * 8 == 64:
                vdappc += "_x86_64"
            else:
                vdappc += "_i686"

        vdappc += "/vdappc"

        if sys.platform == "win32":
            vdappc += ".exe"

        vdappc = os.path.normpath(vdappc)

        self.eabi = eabi
        self.vdappc = vdappc

    def asm_opcodes(self, tmpdir: str, txtfile: str=None) -> str:
        if sys.platform not in PpcFormatter.AVAILABLE_PLATFORMS:
            raise UnsupportedOSError(f"{sys.platform} OS is not supported")
        
        for i in ("as", "ld", "objcopy"):
            if not os.path.isfile(self.eabi[i]):
                raise FileNotFoundError(self.eabi[i] + " not found")

        if txtfile is None:
            txtfile = os.path.join(tmpdir, "code.txt")

        with open(txtfile, 'r+') as asmfile:
            asm = "\n".join([self.sanitize_opcodes(line).replace(";", "#", 1) if line.strip().startswith(("b", ".")) or ":" in line else line.strip("\n").replace(";", "#", 1) for line in asmfile if f".include \"__includes.s\"" not in line]) + "\n"
            asmfile.seek(0)
            asmfile.write(f".include \"__includes.s\"\n" + asm)
        
        tmpfile = os.path.join(tmpdir, "code.bin")

        output = subprocess.run(f'"{self.eabi["as"]}" -mregnames -mgekko -o "{tmpdir}src1.o" "{txtfile}"', shell=True,
                                capture_output=True, text=True)
        if output.stderr:
            errormsg = output.stderr.replace(txtfile + ":", "^")[23:]

            with open(txtfile, "r") as asm:
                assembly = asm.read().split("\n")

            for i, index in enumerate(re.findall(r"(?<=\^)\d+", errormsg)):
                instruction = assembly[int(index, 10) - 1].lstrip()
                errormsg = re.sub(r"(?<! )\^", enclose_string(instruction) + "\n ^", errormsg + "\n\n", count=1)

            raise RuntimeError(errormsg)

        output = subprocess.run(f'"{self.eabi["ld"]}" -Ttext 0x80000000 -o "{tmpdir}src2.o" "{tmpdir}src1.o"', shell=True,
                                capture_output=True, text=True)

        subprocess.run(f'"{self.eabi["objcopy"]}" -O binary "{tmpdir}src2.o" "{tmpfile}"', shell=True)

        rawhex = ""
        try:
            with open(tmpfile, "rb") as f:
                try:
                    rawhex = f.read().hex()
                    rawhex = self._format_rawhex(rawhex).upper()
                except TypeError as e:
                    self.log.exception(e)
                    rawhex = "The compile was corrupt,\nplease try again.\n"
        except IOError:
            with open(txtfile, "r") as asm:
                assembly = asm.read().split("\n")

            self.log.exception("Failed to open '" + tmpfile + "'")
            resSegments = output.stderr.split(r"\r\n")
            for segment in resSegments:
                try:
                    index = int(re.findall(r"(?<=\(\.text\+)[0-9a-fA-Fx]+", segment)[0], 16) >> 2
                    msg = re.findall(r"(?<=\): ).+", segment)[0]
                    instruction = assembly[index + 1].lstrip()
                except (TypeError, IndexError):
                    continue
                rawhex += f"{enclose_string(instruction)}\n ^{index}: Error: {msg}\n\n"

        return rawhex


    def dsm_geckocodes(self, tmpdir: str, txtfile: str=None) -> str:
        if sys.platform not in PpcFormatter.AVAILABLE_PLATFORMS:
            raise UnsupportedOSError(f"{sys.platform} OS is not supported")

        if not os.path.isfile(self.vdappc):
            raise FileNotFoundError(self.vdappc + " not found")

        tmpfile = os.path.join(tmpdir, "code.bin")

        output = subprocess.run(f'"{self.vdappc}" "{tmpfile}" 0', shell=True, capture_output=True, text=True)

        if output.stderr:
            raise RuntimeError(output.stderr)

        opcodes = self._format_opcodes(output.stdout)

        if txtfile is not None:
            try:
                with open(txtfile, "w") as f:
                    f.write(opcodes + "\n")
            except IOError:
                self.log.exception("Failed to open '" + txtfile + "'")

        return opcodes

    @staticmethod
    def _format_rawhex(rawhex: str) -> str:
        # Format raw hex into readable Gecko/WiiRd codes
        code = []

        for i in range(0, len(rawhex), 8):
            code.append(rawhex[i:(i+8)])
        for i in range(1, len(code), 2):
            code[i] += "\n"
        for i in range(0, len(code), 2):
            code[i] += " "

        return "".join(code)

    @staticmethod
    def _format_opcodes(opcodes: str) -> str:
        # Format the output from vdappc
        textOutput = []
        labels = []
        ppcPattern = re.compile(r"([a-fA-F0-9]+)(?:\:  )([a-fA-F0-9]+)(?:\s+)([a-zA-Z.+-_]+)(?:[ \t]+|)([-\w,()]+|)")
        branchLabel = ".loc_0x{:X}:"
        unsignedInstructions = ("lis", "ori", "oris", "xori", "xoris", "andi.", "andis.")
        nonhexInstructions = ("rlwinm", "rlwinm.", "rlwnm", "rlwnm.", "rlwimi", "rlwimi.", "crclr", "crxor",
                              "cror", "crorc", "crand", "crnand", "crandc", "crnor", "creqv", "crse", "crnot", "crmove")
        pairedSingleLoadStores = ("psq_l", "psq_lu", "psq_st", "psq_stu")

        for _ppcOffset, _ppcRaw, _ppcInstruction, _ppcSIMM in re.findall(ppcPattern, opcodes):
            #Branch label stuff
            if _ppcInstruction.startswith("b") and "r" not in _ppcInstruction:
                if _ppcInstruction == "b" or _ppcInstruction == "bl":
                    SIMM = PpcFormatter._sign_extendb(int(_ppcRaw[1:], 16) & 0x3FFFFFC)
                else:
                    SIMM = PpcFormatter._sign_extend16(int(_ppcRaw[4:], 16) & 0xFFFC)

                newSIMM = re.sub("0x-", "-0x", "0x{:X}".format(SIMM))
                offset = int(_ppcOffset, 16) + SIMM
                bInRange = (offset >> 2) > 0 and offset <= len(re.findall(ppcPattern, opcodes)) << 2
                label = branchLabel.format(offset & 0xFFFFFFFC)

                if label not in labels and bInRange is True:
                    labels.append(label)

                if bInRange is True or offset == 0:
                    if "," in _ppcSIMM:
                        textOutput.append("  " + _ppcInstruction.ljust(10, " ") + re.sub(r"(?<=,| )(?:0x| +|)[a-fA-F0-9]+", " " + label[:-1].rstrip(), _ppcSIMM))
                    else:
                        textOutput.append("  " + _ppcInstruction.ljust(10, " ") + label[:-1].rstrip())
                else:
                    if "," in _ppcSIMM:
                        textOutput.append("  " + _ppcInstruction.ljust(10, " ") + re.sub(r"(?<=,| )(?:0x| +|)[a-fA-F0-9]+", " " + newSIMM.rstrip(), _ppcSIMM))
                    else:
                        textOutput.append("  " + _ppcInstruction.ljust(10, " ") + newSIMM.rstrip())
            elif _ppcInstruction[:1] in ("s", "l") and _ppcInstruction.endswith("u") and _ppcSIMM[-4:] == "(r0)":
                textOutput.append("  " + ".long".ljust(10, " ") + "0x" + _ppcRaw)
            else:
                #Set up cleaner format
                values = _ppcSIMM
                if _ppcSIMM.count(",") < 4 or _ppcInstruction in pairedSingleLoadStores:
                    _currentfmtpos = 0
                    for matchObj in re.finditer(r"(?<=,)(?<!r|c)[-\d]+(?!x)(?:\(|)", _ppcSIMM):
                        decimal = matchObj.group()
                        if decimal != "0":
                            if "(" in decimal and _ppcInstruction not in unsignedInstructions:
                                if _ppcInstruction in pairedSingleLoadStores:
                                    decimal = "0x{:X}(".format(PpcFormatter._sign_extendps(int(decimal[:-1], 10)))
                                else:
                                    decimal = "0x{:X}(".format(int(decimal[:-1], 10))
                                decimal = decimal.replace("0x-", "-0x")
                            elif _ppcInstruction not in unsignedInstructions:
                                decimal = "0x{:X}".format(int(decimal, 10))
                                decimal = decimal.replace("0x-", "-0x")
                            else:
                                if int(decimal, 10) < 0:
                                    decimal = "0x{:X}".format(0x10000 - abs(int(decimal, 10)))
                                else:
                                    decimal = "0x{:X}".format(int(decimal, 10))
                            
                        values = values[:_currentfmtpos] + re.sub(r"(?<=,)(?<!r|c)[-\d]+(?!x)(?:\(|)", decimal, values[_currentfmtpos:], count=1)
                        _currentfmtpos = matchObj.end() + (len(decimal) - (matchObj.end() - matchObj.start()))

                    if _ppcInstruction not in pairedSingleLoadStores:
                        values = values.replace(",", ", ")

                elif _ppcInstruction == "crclr" or _ppcInstruction == "crse":
                    values = re.sub(r",\d", "", values)

                textOutput.append("  " + _ppcInstruction.replace(".word", ".long").ljust(10, " ") + values.rstrip())

        #Set up labels in text output
        textOutput.insert(0, branchLabel.format(0))
        for i, label in enumerate(sorted(sorted(labels, key=str), key=len), start=1):
            labelOffset = re.findall("(?:(-0x|0x))([a-fA-F0-9]+)", label)
            labelIndex = (int(labelOffset[0][1], 16) >> 2) + i

            if labelIndex < len(textOutput) and labelIndex >= 0:
                textOutput.insert(labelIndex, "\n" + label)
            elif labelIndex >= 0:
                textOutput.append("\n" + label)
            else:
                textOutput.insert(0, "\n" + label)

        # Return the disassembled opcodes
        return "\n".join(textOutput)

    @staticmethod
    def _sign_extend16(value: int) -> int:
        """ Sign extend a short """
        if value & 0x8000:
            return value - 0x10000
        else:
            return value

    @staticmethod
    def _sign_extend32(value: int) -> int:
        """ Sign extend an int """
        if value & 0x80000000:
            return value - 0x100000000
        else:
            return value

    @staticmethod
    def _sign_extendb(value: int) -> int:
        """ Sign extend a b offset """
        if value & 0x2000000:
            return value - 0x4000000
        else:
            return value

    @staticmethod
    def _sign_extendps(value: int) -> int:
        """ Sign extend a paired single load/store """
        if value & 0x800:
            return value - 0x1000
        else:
            return value

    @staticmethod
    def _align_header(rawhex: str, post: str, codetype: str, numbytes: str) -> str:
        endingZeros = int(numbytes, 16) % 8

        if codetype == "0414":
            post = "00000000"[:(4 - endingZeros)*2]
        elif codetype == "0616":
            if endingZeros > 4:
                post = "00000000 00000000"[1 + endingZeros*2:]
            elif endingZeros > 0:
                post = "00000000 00000000"[endingZeros*2:]
            else:
                post = ""
        elif codetype == "C0":
            if endingZeros > 4:
                post = "00000000 00000000\n4E800020 00000000"[1 + endingZeros*2:]
            elif endingZeros > 0:
                post = "00000000 4E800020"[endingZeros*2:]
            elif post == "4E800020 00000000":
                post = "\n" + post
        elif codetype in ("C2D2", "F2F4"):
            if endingZeros > 4:
                post = "00000000 00000000\n60000000 00000000"[1 + endingZeros*2:]
            elif endingZeros > 0:
                post = "00000000 00000000"[endingZeros*2:]
        return rawhex + post

    @staticmethod
    def construct_code(rawhex: str, bapo: str=None, xor: str=None, chksum: str=None, ctype: str=None) -> str:
        if ctype is None:
            return rawhex

        numlines = "{:X}".format(len(rawhex.split("\n")))
        numbytes = "{:X}".format(len(rawhex.replace("\n", "").replace(" ", "")) >> 1)
        leading_zeros = ["0" * (8 - len(numlines)), "0" * (8 - len(numbytes))]

        try:
            isFailed = False
            int(rawhex.replace("\n", "").replace(" ", ""), 16)
        except ValueError:
            isFailed = True

        if isFailed is False:
            if rawhex[-1] == " ":
                post = " 00000000"
            else:
                post = "\n60000000 00000000"

            if ctype == "C0":
                pre = "C0000000 {}\n".format("".join(leading_zeros[0]) + numlines)
                post = "4E800020" + post[-9:]
            else:
                pre = {"8": "C", "0": "D"}.get(bapo[0], "C")
                if bapo[1] == "1":
                    pre += "3" + bapo[2:] + " "
                else:
                    pre += "2" + bapo[2:] + " "

                if ctype == "0414":
                    pre = {"8": "0", "0": "1"}.get(bapo[0], "0")
                    if bapo[1] == "1":
                        pre += "5"
                    else:
                        pre += "4"

                    newhex = ''
                    address = int(bapo, 16) & 0xFFFFFF

                    for opcodeline in rawhex.split('\n'):
                        for opcode in opcodeline.split(' '):
                            if opcode == '':
                                break
                            newhex += pre + '{:06X} '.format(address) + PpcFormatter._align_header(opcode, post, ctype, "{:X}".format(len(opcode) >> 1)) + '\n'
                            address += 4

                    return newhex

                elif ctype == "0616":
                    pre = {"8": "0", "0": "1"}.get(bapo[0], "0")
                    if bapo[1] == "1":
                        pre += "7" + bapo[2:] + " "
                    else:
                        pre += "6" + bapo[2:] + " "
                    pre += "".join(leading_zeros[1]) + numbytes + "\n"

                elif ctype == "C2D2":
                    pre += "".join(leading_zeros[0]) + numlines + "\n"

                else:  # ctype == "F2F4"
                    if int(numlines, 16) <= 0xFF:
                        pre = "F" + str(int({"D": "2"}.get(pre[0], "0")) + int(pre[1]))
                        if int(numlines, 16) <= 0xF:
                            numlines = "0"+numlines

                        pre += bapo[2:] + " " + "{:02X}".format(int(chksum, 16)) + "{:04X}".format(int(xor, 16)) + numlines + "\n"
                    else:
                        raise CodetypeError("Number of lines (" + numlines + ") must be lower than 0xFF")
            return pre + PpcFormatter._align_header(rawhex[:-1], post, ctype, numbytes)
        else:
            return rawhex

    @staticmethod
    def deconstruct_code(codes: str, cFooter: bool=True) -> str:
        if codes[:2] not in ("04", "14", "05", "15", "06", "07", "16", "17", "C0", "C2", "C3", "D2", "D3", "F2", "F3", "F4", "F5"):
            return (codes, None, None, None, None)

        bapo = None
        xor = None
        chksum = None
        codetype = "C0"

        if codes[:2] != "C0":
            codetype = "C2D2"
            bapo = {"0": "8", "1": "0", "C": "8", "D": "0", "F": "8"}.get(codes[0], "8")
            if codes[1] in ("4", "5") and codes[0] == "F":
                bapo = "0"
            bapo += str(int(codes[1]) % 2) + codes[2:8]

            if codes[0] == "F":
                codetype = "F2F4"
                chksum = codes[9:11]
                xor = codes[11:15]
            elif codes[:2] in ("06", "07", "16", "17"):
                codetype = "0616"
            elif codes[:2] in ("04", "05", "14", "15"):
                codetype = "0414"

        if codetype == "0616":
            length = int(codes[9:17], 16)
            newindex = (length + 3) & -4
            if newindex % 8 == 0:
                return (codes[18:], bapo, xor, chksum, codetype)
            else:
                return (codes[18:-9], bapo, xor, chksum, codetype)

        elif codetype == "0414":
            fcodes = ""
            for i, line in enumerate(codes.split("\n")):
                fcodes += line[9:]
                if i % 2 == 0:
                    fcodes += " "
                else:
                    fcodes += "\n"
            return (fcodes.strip(), bapo, xor, chksum, codetype)

        if codes[-17:-9] == "60000000" or (codes[-17:] == "4E800020 00000000" and codetype == "C0" and cFooter):
            return (codes[18:-17], bapo, xor, chksum, codetype)
        else:
            return (codes[18:-9], bapo, xor, chksum, codetype)

    @staticmethod
    def sanitize_opcodes(label: str) -> str:
        label = label.rstrip()
        ppcPattern = re.compile(r"(?:\s+)([a-zA-Z.+-_]+)(?:[ \t]+|)([\. \t\-\w,()]+|)")
        sanitize_list = "abcdefghijklmnopqrstuvwxyz1234567890.#"
        whitespace = " \n\t\r"
        iscomment = False
        isparen = False
        isinstruction = True

        newstr = []
        try:
            _ppcInstruction, _ppcSIMM = re.findall(ppcPattern, label)[0]
        except IndexError:
            pass
        else:
            if "," in _ppcSIMM:
                ofs = re.compile(r"(?<=[\+\-\s]).+")
            else:
                ofs = re.compile(r".+")

            if _ppcInstruction == ".asciz":
                return label
            elif _ppcInstruction.startswith("b") and "r" not in _ppcInstruction:
                try:
                    int(re.findall(ofs, _ppcSIMM)[0])
                    return label
                except ValueError:
                    try:
                        int(re.findall(ofs, _ppcSIMM)[0], 16)
                        return label
                    except ValueError:
                        pass

        for i, char in enumerate(label):

            if char == "#":
                newstr = "".join(newstr)
                if newstr.startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")):
                    return newstr[1:] + label[i:]
                else:
                    return newstr + label[i:]
            elif char == "(" and iscomment is False:
                isparen = True
            elif char == ")":
                isparen = False

            if char == "." and iscomment is False and i+2 < len(label) and isinstruction == True:
                if label[i+1] != "s" or label[i+2] != "e":
                    return label

            if i > 0 and char in whitespace and label[i-1] not in whitespace:
                isinstruction = False

            if char not in sanitize_list and char not in sanitize_list.upper() and not iscomment:
                if isparen and char in ", ":
                    newstr.append("_")
                    continue

                if isinstruction and char in "-+":
                    newstr.append(char)
                    continue

                if i+1 < len(label):
                    if char in ":," and label[i+1] in whitespace:
                        newstr.append(char)
                    elif char in whitespace:
                        newstr.append(char)
                    else:
                        newstr.append("_")
                else:
                    if char in whitespace or char in ":,":
                        newstr.append(char)
                    else:
                        newstr.append("_")
            else:
                newstr.append(char)

        newstr = "".join(newstr)
        if newstr.startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")):
            return newstr[1:]
        else:
            return newstr