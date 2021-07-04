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

import logging
import re
import subprocess
import sys
from pathlib import Path
from struct import calcsize
from typing import Optional, Tuple, Union

from errors import CodetypeError, UnsupportedOSError
from geckolibs.geckocode import *


def enclose_string(string: str) -> str:
    return "-"*(len(string) + 2) + "\n|" + string + "|\n" + "-"*(len(string) + 2)


def resource_path(relative_path: str = "") -> Path:
    """ Get absolute path to resource, works for dev and for cx_freeze """
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / relative_path
    else:
        if getattr(sys, "frozen", False):
            # The application is frozen
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent

        return base_path / relative_path


def get_program_folder(folder: str = "") -> Path:
    """ Get path to appdata """
    from os import getenv

    if sys.platform == "win32":
        datapath = Path(getenv("APPDATA")) / folder
    elif sys.platform == "darwin":
        if folder:
            folder = "." + folder
        datapath = Path("~/Library/Application Support").expanduser() / folder
    elif "linux" in sys.platform:
        if folder:
            folder = "." + folder
        datapath = Path.home() / folder
    else:
        raise NotImplementedError(f"{sys.platform} OS is unsupported")
    return datapath


class PpcFormatter(object):

    class _CodePacket(object):
        def __init__(self, data: str = "", codetype: GeckoCommand.Type = None, bapo: str = None, xor: str = None, checksum: str = None):
            self.data = data
            self.codetype = codetype
            self.bapo = bapo
            self.xor = xor
            self.checksum = checksum

    SupportedPlatforms = {"darwin", "linux", "win32"}

    def __init__(self):
        if not get_program_folder("PyiiASMH-3").exists():
            get_program_folder("PyiiASMH-3").mkdir()

        self.eabi = None
        self.vdappc = None

        self.log = logging.getLogger("PyiiASMH")
        hdlr = logging.FileHandler(
            str(get_program_folder("PyiiASMH-3") / "error.log"))
        formatter = logging.Formatter(
            "\n%(levelname)s (%(asctime)s): %(message)s")
        hdlr.setFormatter(formatter)
        self.log.addHandler(hdlr)

        self._init_lib()

    def asm_opcodes(self, tmpdir: Union[str, Path], txtfile: Union[str, Path] = None) -> str:
        if sys.platform not in PpcFormatter.SupportedPlatforms:
            raise UnsupportedOSError(f"{sys.platform} OS is not supported")

        for x in ("as", "ld", "objcopy"):
            if not self.eabi[x].is_file():
                raise FileNotFoundError(f"{self.eabi[x]} not found")

        if txtfile is None:
            txtfile = Path(tmpdir, "code.txt")
        elif isinstance(txtfile, str):
            txtfile = Path(txtfile)

        tmpbin = Path(tmpdir, "code.bin")

        with txtfile.open("r") as f:
            includeLine = f".include \"{resource_path('__includes.s')}\"".replace("\\", "/")
            _asm = ""
            i = 0
            for line in f:
                if includeLine in line:
                    continue

                stripped = line.strip()
                if stripped == "":
                    continue

                if re.match(r"#inject\(0x[0-9a-fA-F]{8}\)", stripped) and i == 0:
                    self.bapo = stripped[10:18]

                _asm += stripped.replace(";", "#", 1) + "\n"
                i += 1
            _asm = f"{includeLine}\n.set INJECTADDR, 0x{self.bapo if self.bapo else '80000000'}\n\n{_asm}"

        with txtfile.open("w") as f:
            f.write(_asm)

        output = subprocess.run(f'"{self.eabi["as"]}" -mregnames -mgekko -o "{tmpdir}src1.o" "{txtfile}"', shell=True,
                                capture_output=True, text=True)
        if output.stderr:
            errormsg = output.stderr.replace(f"{txtfile}:", "^")[23:]

            with txtfile.open("r") as f:
                assembly = f.read().split("\n")

            for index in re.findall(r"(?<=\^)\d+", errormsg):
                instruction = assembly[int(index, 10) - 1].lstrip()
                errormsg = re.sub(r"(?<! )\^", enclose_string(
                    instruction) + "\n ^", errormsg + "\n\n", count=1)

            raise RuntimeError(errormsg)

        output = subprocess.run(f'"{self.eabi["ld"]}" -Ttext 0x80000000 -o "{tmpdir}src2.o" "{tmpdir}src1.o"', shell=True,
                                capture_output=True, text=True)

        subprocess.run(
            f'"{self.eabi["objcopy"]}" -O binary "{tmpdir}src2.o" "{tmpbin}"', shell=True)

        rawhex = ""
        try:
            with tmpbin.open("rb") as f:
                try:
                    rawhex = f.read().hex()
                    rawhex = self._format_rawhex(rawhex).upper()
                except TypeError as e:
                    self.log.exception(e)
                    rawhex = "The compile was corrupt,\nplease try again.\n"
        except IOError:
            with txtfile.open("r") as f:
                assembly = f.read().split("\n")

            self.log.exception(f"Failed to open '{tmpbin}'")
            resSegments = output.stderr.split(r"\r\n")
            for segment in resSegments:
                try:
                    index = int(re.findall(
                        r"(?<=\(\.text\+)[0-9a-fA-Fx]+", segment)[0], 16) >> 2
                    msg = re.findall(r"(?<=\): ).+", segment)[0]
                    instruction = assembly[index + 1].lstrip()
                except (TypeError, IndexError):
                    continue
                rawhex += f"{enclose_string(instruction)}\n ^{index}: Error: {msg}\n\n"

        return rawhex

    def dsm_geckocodes(self, tmpdir: Union[str, Path], txtfile: Optional[Union[str, Path]] = None) -> str:
        if sys.platform not in PpcFormatter.SupportedPlatforms:
            raise UnsupportedOSError(f"{sys.platform} OS is not supported")

        if not self.vdappc.is_file():
            raise FileNotFoundError(self.vdappc + " not found")

        tmpfile = Path(tmpdir, "code.bin")

        output = subprocess.run(
            f'"{self.vdappc}" "{tmpfile}" 0', shell=True, capture_output=True, text=True)

        if output.stderr:
            raise RuntimeError(output.stderr)

        opcodes = self._format_opcodes(output.stdout)

        if isinstance(txtfile, str):
            txtfile = Path(txtfile)

        if txtfile is not None:
            try:
                with txtfile.open("w") as f:
                    f.write(opcodes + "\n")
            except IOError:
                self.log.exception(f"Failed to open '{txtfile}'")

        return opcodes

    def _init_lib(self):
        eabi = {}

        # Pathnames for powerpc-eabi executables
        for x in ("as", "ld", "objcopy"):
            eabi[x] = self._create_lib_path(f"powerpc-eabi-{x}")

        self.eabi = eabi
        self.vdappc = self._create_lib_path("vdappc")

    @staticmethod
    def _create_lib_path(name: str) -> Path:
        _libPath = str(resource_path(f"lib/{sys.platform}"))

        if sys.platform == "linux":
            if calcsize("P") * 8 == 64:
                _libPath += "_x86_64"
            else:
                _libPath += "_i686"

        _libPath += f"/{name}"

        if sys.platform == "win32":
            _libPath += ".exe"

        return Path(_libPath).resolve()

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
        BRANCHLABEL = ".loc_0x{:X}:"
        # NONHEXINSTRUCTIONS = ("rlwinm", "rlwinm.", "rlwnm", "rlwnm.", "rlwimi", "rlwimi.", "crclr", "crxor",
        #                      "cror", "crorc", "crand", "crnand", "crandc", "crnor", "creqv", "crse", "crnot", "crmove")
        PPCPATTERN = re.compile(
            r"([a-fA-F0-9]+)(?:\:  )([a-fA-F0-9]+)(?:\s+)([a-zA-Z.+-_]+)(?:[ \t]+|)([-\w,()]+|)")
        PSLOADSTORES = ("psq_l", "psq_lu", "psq_st", "psq_stu")
        UNSIGNEDINSTRUCTIONS = ("lis", "ori", "oris",
                                "xori", "xoris", "andi.", "andis.")

        # Format the output from vdappc
        _textOutput = []
        _labels = []

        for PPCOFFSET, PPCRAW, PPCINSTRUCTION, PPCSIMM in re.findall(PPCPATTERN, opcodes):
            # Branch label stuff
            if PPCINSTRUCTION.startswith("b") and "r" not in PPCINSTRUCTION:
                if PPCINSTRUCTION == "b" or PPCINSTRUCTION == "bl":
                    SIMM = PpcFormatter._sign_extendb(
                        int(PPCRAW[1:], 16) & 0x3FFFFFC)
                else:
                    SIMM = PpcFormatter._sign_extend16(
                        int(PPCRAW[4:], 16) & 0xFFFC)

                newSIMM = re.sub("0x-", "-0x", "0x{:X}".format(SIMM))
                offset = int(PPCOFFSET, 16) + SIMM
                bInRange = (offset >> 2) > 0 and offset <= len(
                    re.findall(PPCPATTERN, opcodes)) << 2
                label = BRANCHLABEL.format(offset & 0xFFFFFFFC)

                if label not in _labels and bInRange is True:
                    _labels.append(label)

                if bInRange is True or offset == 0:
                    if "," in PPCSIMM:
                        _textOutput.append("  " + PPCINSTRUCTION.ljust(10, " ") + re.sub(
                            r"(?<=,| )(?:0x| +|)[a-fA-F0-9]+", " " + label[:-1].rstrip(), PPCSIMM))
                    else:
                        _textOutput.append(
                            "  " + PPCINSTRUCTION.ljust(10, " ") + label[:-1].rstrip())
                else:
                    if "," in PPCSIMM:
                        _textOutput.append("  " + PPCINSTRUCTION.ljust(10, " ") + re.sub(
                            r"(?<=,| )(?:0x| +|)[a-fA-F0-9]+", " " + newSIMM.rstrip(), PPCSIMM))
                    else:
                        _textOutput.append(
                            "  " + PPCINSTRUCTION.ljust(10, " ") + newSIMM.rstrip())
            elif PPCINSTRUCTION[:1] in ("s", "l") and PPCINSTRUCTION.endswith("u") and PPCSIMM[-4:] == "(r0)":
                _textOutput.append(
                    "  " + ".long".ljust(10, " ") + "0x" + PPCRAW)
            else:
                # Set up cleaner format
                values = PPCSIMM
                if PPCSIMM.count(",") < 4 or PPCINSTRUCTION in PSLOADSTORES:
                    _currentfmtpos = 0
                    for matchObj in re.finditer(r"(?<=,)(?<!r|c)[-\d]+(?!x)(?:\(|)", PPCSIMM):
                        decimal = matchObj.group()
                        if decimal != "0":
                            if "(" in decimal and PPCINSTRUCTION not in UNSIGNEDINSTRUCTIONS:
                                if PPCINSTRUCTION in PSLOADSTORES:
                                    decimal = "0x{:X}(".format(
                                        PpcFormatter._sign_extendps(int(decimal[:-1], 10)))
                                else:
                                    decimal = "0x{:X}(".format(
                                        int(decimal[:-1], 10))
                                decimal = decimal.replace("0x-", "-0x")
                            elif PPCINSTRUCTION not in UNSIGNEDINSTRUCTIONS:
                                decimal = "0x{:X}".format(int(decimal, 10))
                                decimal = decimal.replace("0x-", "-0x")
                            else:
                                if int(decimal, 10) < 0:
                                    decimal = "0x{:X}".format(
                                        0x10000 - abs(int(decimal, 10)))
                                else:
                                    decimal = "0x{:X}".format(int(decimal, 10))

                        values = values[:_currentfmtpos] + re.sub(
                            r"(?<=,)(?<!r|c)[-\d]+(?!x)(?:\(|)", decimal, values[_currentfmtpos:], count=1)
                        _currentfmtpos = matchObj.end() + (len(decimal) - (matchObj.end() - matchObj.start()))

                    if PPCINSTRUCTION not in PSLOADSTORES:
                        values = values.replace(",", ", ")

                elif PPCINSTRUCTION == "crclr" or PPCINSTRUCTION == "crse":
                    values = re.sub(r",\d", "", values)

                _textOutput.append(
                    "  " + PPCINSTRUCTION.replace(".word", ".long").ljust(10, " ") + values.rstrip())

        # Set up _labels in text output
        _textOutput.insert(0, BRANCHLABEL.format(0))
        for i, label in enumerate(sorted(sorted(_labels, key=str), key=len), start=1):
            labelOffset = re.findall("(?:(-0x|0x))([a-fA-F0-9]+)", label)
            labelIndex = (int(labelOffset[0][1], 16) >> 2) + i

            if labelIndex < len(_textOutput) and labelIndex >= 0:
                _textOutput.insert(labelIndex, "\n" + label)
            elif labelIndex >= 0:
                _textOutput.append("\n" + label)
            else:
                _textOutput.insert(0, "\n" + label)

        # Return the disassembled opcodes
        return "\n".join(_textOutput)

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
    def _align_header(rawhex: str, post: str, codetype: GeckoCommand.Type, numbytes: str) -> str:
        endingZeros = int(numbytes, 16) % 8

        if codetype == Write32.codetype:
            post = "00000000"[:(4 - endingZeros)*2]
        elif codetype == WriteString.codetype:
            if endingZeros > 4:
                post = "00000000 00000000"[1 + endingZeros*2:]
            elif endingZeros > 0:
                post = "00000000 00000000"[endingZeros*2:]
            else:
                post = ""
        elif codetype == AsmExecute.codetype:
            if endingZeros > 4:
                post = "00000000 00000000\n4E800020 00000000"[
                    1 + endingZeros*2:]
            elif endingZeros > 0:
                post = "00000000 4E800020"[endingZeros*2:]
            elif post == "4E800020 00000000":
                post = "\n" + post
        elif codetype in {AsmInsert.codetype, AsmInsertLink.codetype, AsmInsertXOR.codetype}:
            if endingZeros > 4:
                post = "00000000 00000000\n60000000 00000000"[
                    1 + endingZeros*2:]
            elif endingZeros > 0:
                post = "00000000 00000000"[endingZeros*2:]
        return rawhex + post

    def construct_code(self,
                       rawhex: str,
                       bapo: Optional[str] = None,
                       xor: Optional[str] = None,
                       chksum: Optional[str] = None,
                       ctype: Optional[GeckoCommand.Type] = None) -> str:
        if ctype is None:
            return rawhex

        numlines = "{:X}".format(len(rawhex.split("\n")))
        numbytes = "{:X}".format(
            len(rawhex.replace("\n", "").replace(" ", "")) >> 1)
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

            if ctype == Write32.codetype:
                pre = {"8": "0", "0": "1"}.get(bapo[0], "0")
                if bapo[1] == "1":
                    pre += "5"
                else:
                    pre += "4"

                newhex = ""
                address = int(bapo, 16) & 0xFFFFFF

                for opcodeline in rawhex.split("\n"):
                    for opcode in opcodeline.split(" "):
                        if opcode == "":
                            break
                        newhex += pre + "{:06X} ".format(address) + PpcFormatter._align_header(
                            opcode, post, ctype, "{:X}".format(len(opcode) >> 1)) + '\n'
                        address += 4

                return newhex

            elif ctype == WriteString.codetype:
                pre = {"8": "0", "0": "1"}.get(bapo[0], "0")
                if bapo[1] == "1":
                    pre += "7" + bapo[2:] + " "
                else:
                    pre += "6" + bapo[2:] + " "
                pre += "".join(leading_zeros[1]) + numbytes + "\n"
            elif ctype == AsmExecute.codetype:
                pre = "C0000000 {}\n".format(
                    "".join(leading_zeros[0]) + numlines)
                post = "4E800020" + post[-9:]
            elif ctype == AsmInsert.codetype:
                pre = {"8": "C", "0": "D"}.get(bapo[0], "C")
                if bapo[1] == "1":
                    pre += "3" + bapo[2:] + " "
                else:
                    pre += "2" + bapo[2:] + " "
                pre += "".join(leading_zeros[0]) + numlines + "\n"
            elif ctype == AsmInsertLink.codetype:
                pre = {"8": "C", "0": "D"}.get(bapo[0], "C")
                if bapo[1] == "1":
                    pre += "5" + bapo[2:] + " "
                else:
                    pre += "4" + bapo[2:] + " "
                pre += "".join(leading_zeros[0]) + numlines + "\n"

            else:  # ctype == "F2F4"
                if int(numlines, 16) <= 0xFF:
                    pre = "F"
                    if bapo[1] == "1":
                        pre += ("5" if bapo[1] == "1" else "3") + bapo[2:] + " "
                    else:
                        pre += ("4" if bapo[1] == "1" else "2") + bapo[2:] + " "
                    if int(numlines, 16) <= 0xF:
                        numlines = f"0{numlines}"

                    pre += f"{chksum}{xor}{numlines}\n"
                else:
                    raise CodetypeError(
                        f"Number of lines ({numlines}) must be lower than 0xFF")
            return pre + PpcFormatter._align_header(rawhex[:-1], post, ctype, numbytes)
        else:
            return rawhex

    def deconstruct_code(self, codes: str, cFooter: bool = True) -> _CodePacket:
        packet = PpcFormatter._CodePacket()
        for char in "".join(codes.split()):
            if char not in "0123456789abcdefABCDEF":
                self.log.exception(
                    "Code passed to deconstruct_code has invalid characters")
                return PpcFormatter._CodePacket(None)

        if codes[:2] in {"04", "14", "05", "15", "06", "07", "16", "17", "C0", "C2", "C3", "D2", "D3", "C4", "D4", "C5", "D5", "F2", "F3", "F4", "F5"}:
            geckocommand = GeckoCommand.str_to_geckocommand(codes)
            packet.codetype = geckocommand.codetype
            if hasattr(geckocommand, "_address"):
                if geckocommand.is_po_type():
                    packet.bapo = f"{geckocommand._address | (0x80000000 if geckocommand._isPointerType else 0):8X}"
                else:
                    packet.bapo = f"{geckocommand._address | 0x80000000:8X}"
            if geckocommand == Write32:
                fcodes = ""
                for i, line in enumerate(codes.split("\n")):
                    fcodes += line[9:]
                    if i % 2 == 0:
                        fcodes += " "
                    else:
                        fcodes += "\n"
                packet.data = fcodes.strip()
            elif geckocommand == WriteString:
                length = int(codes[9:17], 16)
                newindex = (length + 3) & -4
                if newindex % 8 == 0:
                    packet.data = codes[18:]
                else:
                    packet.data = codes[18:-9]
            elif geckocommand == AsmExecute:
                if codes[-17:-9] == "60000000" or (codes[-17:] == "4E800020 00000000" and cFooter):
                    packet.data = codes[18:-17]
                else:
                    packet.data = codes[18:-9]
            elif geckocommand == AsmInsert:
                if codes[-17:-9] == "60000000" or (codes[-17:] == "4E800020 00000000"):
                    packet.data = codes[18:-17]
                else:
                    packet.data = codes[18:-9]
            elif geckocommand == AsmInsertLink:
                if codes[-17:-9] == "60000000" or (codes[-17:] == "4E800020 00000000"):
                    packet.data = codes[18:-17]
                else:
                    packet.data = codes[18:-9]
            elif geckocommand == AsmInsertXOR:
                packet.checksum = codes[9:11]
                packet.xor = codes[11:15]
        else:
            packet.data = codes

        return packet

    @staticmethod
    def _first_instance_of(char: str, string: str, _start: int = -1, _end: int = -1) -> Tuple[str, int]:
        """ Return the character and first occuring index of in a list """
        if _start == -1:
            _start = 0
        if _end == -1:
            _end = len(string)

        if isinstance(char, str):
            return char, string.find(char, _start, _end)
        else:
            char = list(char)  # ensure mutable
            returnchar = ["", -1]
            for _char in char:
                if returnchar[0] == "" and string.find(_char, _start, _end) > -1:
                    returnchar = [_char, string.find(_char, _start, _end)]
                else:
                    if string.find(_char, _start, _end) < returnchar[1] and string.find(_char, _start, _end) > -1:
                        returnchar = [_char, string.find(_char, _start, _end)]
            return returnchar

    @staticmethod
    def _parse_ppc(line: str) -> Tuple[str, str, str]:
        """ Returns a tuple containing (instr., simm, comment) """

        _line = line.strip()

        PPCINSTRUCTION = None
        PPCSIMM = None
        _ppcComment = None

        if _line.startswith(("#", ";")):
            return None, None, _line
        elif _line == "":
            return None, None, None

        commentIndex = PpcFormatter._first_instance_of(("#", ";"), _line)[1]
        if commentIndex >= 0:
            _ppcComment = _line[commentIndex:]

        if commentIndex >= 0:
            if _line.find(":") >= 0 and _line.find(":") < commentIndex:
                return _line[:commentIndex].strip(), None, _ppcComment
            else:
                if len(_line[:commentIndex].split(" ", maxsplit=1)) == 2:
                    PPCINSTRUCTION, PPCSIMM = _line[:commentIndex].split(
                        " ", maxsplit=1)
                elif len(_line[:commentIndex].split(" ", maxsplit=1)) == 1:
                    PPCINSTRUCTION = _line[:commentIndex].strip()
        else:
            if _line.find(":") >= 0:
                return _line[:commentIndex].strip(), None, None
            else:
                if len(_line.split(" ", maxsplit=1)) == 2:
                    PPCINSTRUCTION, PPCSIMM = _line.split(" ", maxsplit=1)
                elif len(_line.split(" ", maxsplit=1)) == 1:
                    PPCINSTRUCTION = _line.strip()

        return PPCINSTRUCTION, PPCSIMM, _ppcComment

    @staticmethod
    def sanitize_opcodes(opcode: str) -> str:
        opcode = opcode.rstrip()
        PPCINSTRUCTION, PPCSIMM, _ppcComment = PpcFormatter._parse_ppc(opcode)

        registerGex = re.compile(r"[crf]+\d{2}|[crf]+\d{1}")
        sanitizeGex = re.compile(r"[^\w\n@.\"';#]")

        isParen = False

        newSIMM = ""

        if PPCINSTRUCTION is None:
            return opcode.replace(";", "#", 1)
        else:
            if PPCINSTRUCTION.startswith(("b", ".")) and PPCSIMM is not None:
                if PPCINSTRUCTION != ".else" and "if" not in PPCINSTRUCTION:

                    fmtArray = []
                    if PPCSIMM.find("(") >= 0:
                        if PPCSIMM[PPCSIMM.find("(")-1] not in "+-*/^|& \t":
                            print(PPCSIMM, "Successfully found label")
                            return opcode.replace(";", "#", 1)
                            # TODO: Separate label from any mathmatical instructions

                    for section in re.split(r"[,\s]+", PPCSIMM):
                        section = section.strip()
                        if section == "":
                            continue

                        isRegister = True

                        if section in ("==", "||", "&&"):
                            fmtArray.append([section, isParen])
                            continue

                        try:
                            re.findall(registerGex, section)[0]
                        except IndexError:
                            isRegister = False

                        if not isRegister:
                            if not section.startswith("("):
                                closingParen = section.find(")")
                                splitIndex = PpcFormatter._first_instance_of(
                                    ("+", "-", "/", "*", "^", "|", "&"), section.strip("(").strip(")"))[1]

                                section = re.sub(sanitizeGex, "_", section)
                                if closingParen > -1 and isParen is True:
                                    section = section[:closingParen] + \
                                        ")" + section[closingParen + 1:]
                                    isParen = False
                            else:
                                section = "(" + re.sub(sanitizeGex,
                                                       "_", section)[1:]
                                isParen = True

                        fmtArray.append([section, isParen])

                    for i, section in enumerate(fmtArray):
                        if section[1] is True or i < 1:
                            newSIMM += " " + section[0]
                        else:
                            newSIMM += ", " + section[0]

                    return (PPCINSTRUCTION + newSIMM).replace(";", "#", 1)
            elif PPCINSTRUCTION.endswith(":"):
                if _ppcComment is not None:
                    return re.sub(sanitizeGex, "_", PPCINSTRUCTION)[:-1] + ": " + _ppcComment
                else:
                    return re.sub(sanitizeGex, "_", PPCINSTRUCTION)[:-1] + ":"

            return opcode.replace(";", "#", 1)
