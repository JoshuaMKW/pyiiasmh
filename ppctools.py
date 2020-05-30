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
import time
import shutil
import logging
import binascii
import subprocess

from struct import calcsize
from errors import CodetypeError, UnsupportedOSError

log = None
eabi = {}
vdappc = ""


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(
        os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def setup():
    global eabi, vdappc, log

    # Simple check to help prevent this from being run multiple times
    if log is not None or eabi != {} or vdappc != "":
        return

    # Pathnames for powerpc-eabi executables
    for i in ("as", "ld", "objcopy"):
        eabi[i] = resource_path("lib/" + sys.platform)

        if sys.platform == "linux2":
            if calcsize("P") * 8 == 64:
                eabi[i] += "_x86_64"
            else:
                eabi[i] += "_i686"

        eabi[i] += "/powerpc-eabi-" + i

        if sys.platform == "win32":
            eabi[i] += ".exe"

    # Pathname for vdappc executable
    vdappc = resource_path("lib/" + sys.platform)

    if sys.platform == "linux2":
        if calcsize("P") * 8 == 64:
            vdappc += "_x86_64"
        else:
            vdappc += "_i686"

    vdappc += "/vdappc"

    if sys.platform == "win32":
        vdappc += ".exe"

    log = logging.getLogger("PyiiASMH")
    hdlr = logging.FileHandler("error.log")
    formatter = logging.Formatter("\n%(levelname)s (%(asctime)s): %(message)s")
    hdlr.setFormatter(formatter)
    log.addHandler(hdlr)


def asm_opcodes(tmpdir, txtfile, binfile):
    if sys.platform not in ("darwin", "linux2", "win32"):
        raise UnsupportedOSError("'" + sys.platform + "' os is not supported")
    for i in ("as", "ld", "objcopy"):
        if not os.path.isfile(eabi[i]):
            raise IOError(eabi[i] + " not found")

    if txtfile is None:
        txtfile = tmpdir + "code.txt"
    if binfile is None:
        binfile = tmpdir + "code.bin"

    output = subprocess.Popen([eabi["as"], "-mregnames", "-mgekko", "-o",
                               tmpdir + "src1.o", txtfile], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).communicate()

    if output[1]:
        errormsg = str(output[1], encoding="utf-8")
        errormsg = errormsg.replace(txtfile + ":", "^")[23:]

        with open(txtfile, "r") as asm:
            assembly = asm.read()
            for i, index in enumerate(re.findall(r"(?<=\^)\d+", errormsg)):
                instruction = assembly.split("\n")[int(index, 10) - 1].lstrip()
                errormsg = re.sub(r"(?<! )\^", enclose_string(instruction) + "\n ^", errormsg + "\n\n", count=1)

        raise RuntimeError(errormsg)

    subprocess.Popen([eabi["ld"], "-Ttext", "0x80000000", "-o",
                      tmpdir+"src2.o", tmpdir+"src1.o"], stderr=subprocess.PIPE).communicate()

    subprocess.Popen([eabi["objcopy"], "-O", "binary",
                      tmpdir + "src2.o", binfile], stderr=subprocess.PIPE).communicate()

    rawhex = ""
    try:
        f = open(binfile, "rb")
    except IOError:
        log.exception("Failed to open '" + binfile + "'")
        rawhex = "Failed to compile the asm,\nplease try again.\n"
    else:
        try:
            f.seek(0)
            rawhex = f.read().hex()
            rawhex = format_rawhex(rawhex).upper()
        except IOError:
            log.exception("Failed to read '" + binfile + "'")
            rawhex = "Failed to read the gecko code,\nplease try again.\n"
        except TypeError as e:
            log.exception(e)
            rawhex = "The compile was corrupt,\nplease try again.\n"
        finally:
            f.close()
    finally:
        return rawhex


def dsm_geckocodes(tmpdir, txtfile, binfile):
    if sys.platform not in ("linux2", "darwin", "win32"):
        raise UnsupportedOSError("'" + sys.platform + "' os is not supported")
    if not os.path.isfile(vdappc):
        raise IOError(vdappc + " not found")

    if binfile is None:
        binfile = tmpdir + "code.bin"

    output = subprocess.Popen([vdappc, binfile, "0"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).communicate()

    if output[1]:
        raise RuntimeError(output[1])

    opcodes = format_opcodes(str(output[0]))

    if txtfile is not None:
        try:
            f = open(txtfile, "w")
        except IOError:
            log.exception("Failed to open '" + txtfile + "'")
        else:
            try:
                f.write(opcodes + "\n")
            except IOError:
                log.exception("Failed to write to '" + txtfile + "'")
            finally:
                f.close()

    return opcodes


def format_rawhex(rawhex):
    # Format raw hex into readable Gecko/WiiRd codes
    code = []

    for i in range(0, len(rawhex), 8):
        code.append(rawhex[i:(i+8)])

    for i in range(1, len(code), 2):
        code[i] += "\n"
    for i in range(0, len(code), 2):
        code[i] += " "

    return "".join(code)


def format_opcodes(output):
    # Format the output from vdappc
    textoutput = []
    labels = []
    ppc_pattern = re.compile(r"(?:b'|\\r\\n)([a-fA-F0-9]+)(?:\:  )([a-fA-F0-9]+)(?:\\t)([a-zA-Z.+-]+)(?:\\t|)([-\w,()]+|)")
    branch_label = ".loc_0x{:X}:"
    unsigned_instructions = ["lis", "ori", "oris", "xori", "xoris",
                             "andi.", "andis."]
    nonhex_instructions = ["rlwinm", "rlwinm.", "rlwnm", "rlwnm.",
                           "rlwimi", "rlwimi.", "crclr", "crxor",
                           "cror", "crorc", "crand", "crnand",
                           "crandc", "crnor", "creqv", "crse",
                           "crnot", "crmove"]

    for ppc in re.findall(ppc_pattern, output):
        #Branch label stuff
        if ppc[2].startswith("b") and "r" not in ppc[2]:
            if ppc[2] == "b" or ppc[2] == "bl":
                SIMM = sign_extendb(int(ppc[1][1:], 16) & 0x3FFFFFC)
            else:
                SIMM = sign_extend16(int(ppc[1][4:], 16) & 0xFFFC)
            newSIMM = re.sub("0x-", "-0x", "0x{:X}".format(SIMM))
            offset = int(ppc[0], 16) + SIMM
            bInRange = offset >= 0 and offset <= len(re.findall(ppc_pattern, output)) << 2
            label = branch_label.format(offset & 0xFFFFFFFC)
            if label and label not in labels and bInRange == True:
                labels.append(label)
            if bInRange == True:
                if "," in ppc[3]:
                    textoutput.append("  " + ppc[2] + " " + re.sub(r"(?<=,| )(?:0x| +|)[a-fA-F0-9]+", " " + label[:-1].rstrip(), ppc[3]))
                else:
                    textoutput.append("  " + ppc[2] + " " + label[:-1].rstrip())
            else:
                if "," in ppc[3]:
                    textoutput.append("  " + ppc[2] + " " + re.sub(r"(?<=,| )(?:0x| +|)[a-fA-F0-9]+", " " + newSIMM.rstrip(), ppc[3]))
                else:
                    textoutput.append("  " + ppc[2] + " " + newSIMM.rstrip())
        else:
            #Set up cleaner format
            values = ppc[3]
            if ppc[2] not in nonhex_instructions:
                #Format decimal values to be hex
                for decimal in re.findall(r"(?<=,)(?<!r|c)[-\d]+(?!x)(?:\(|)", ppc[3]):
                    if "(" in decimal and ppc[2] not in unsigned_instructions:
                        decimal = "0x{:X}(".format(int(decimal[:-1], 10))
                        decimal = re.sub(r"0x-", "-0x", decimal)
                    elif ppc[2] not in unsigned_instructions:
                        decimal = "0x{:X}".format(int(decimal, 10))
                        decimal = re.sub(r"0x-", "-0x", decimal)
                    else:
                        if int(decimal, 10) < 0:
                            decimal = "0x{:X}".format(0x10000 - abs(int(decimal, 10)))
                        else:
                            decimal = "0x{:X}".format(int(decimal, 10))
                    values = re.sub(r"(?<=,)(?<!r|c)[-\d]+(?!x)(?:\(|)", decimal, values, count=1)
                values = re.sub(",", ", ", values)
            elif ppc[2] == "crclr" or ppc[2] == "crse":
                values = re.sub(r",\d", "", values)
            textoutput.append("  " + ppc[2].replace("word", "long") + " " + values.rstrip())

    #Set up labels in text output
    textoutput.insert(0, branch_label.format(0))
    for i, label in enumerate(sorted(sorted(labels, key=str), key=len), start=1):
        labeloffset = re.findall("(?:(-0x|0x))([a-fA-F0-9]+)", label)
        labelIndex = (int(labeloffset[0][1], 16) >> 2) + i
        if labelIndex < len(textoutput) and labelIndex >= 0:
            textoutput.insert(labelIndex, "\n" + label)
        elif labelIndex >= 0:
            textoutput.insert(len(textoutput) - 1, "\n" + label)
        else:
            textoutput.insert(0, "\n" + label)

    # Return the disassembled opcodes
    return "\n".join(textoutput)

def sign_extend16(value):
    """ Sign extend a short """
    if value & 0x8000:
        return value - 0x10000
    else:
        return value

def sign_extend32(value):
    """Sign extend an int """
    if value & 0x80000000:
        return value - 0x100000000
    else:
        return value

def sign_extendb(value):
    """Sign extend a b offset"""
    if value & 0x2000000:
        return value - 0x4000000
    else:
        return value

def enclose_string(string):
    return "-"*(len(string) + 2) + "\n|" + string + "|\n" + "-"*(len(string) + 2)

def alignHeader(rawhex, post, codetype, numbytes):
    endingZeros = int(numbytes, 16) % 8
    if codetype == "0616":
        if endingZeros > 4:
            post = "00000000 00000000"[1 + endingZeros * 2:]
        elif endingZeros > 0:
            post = "00000000 00000000"[endingZeros * 2:]
        else:
            post = ""
    elif codetype == "C0":
        if endingZeros > 4:
            post = "00000000 00000000\n4E800020 00000000"[1 + endingZeros * 2:]
        elif endingZeros > 0:
            post = "00000000 4E800020"[endingZeros * 2:]
        elif post == "4E800020 00000000":
            post = "\n" + post
    elif codetype in ("C2D2", "F2F4"):
        if endingZeros > 4:
            post = "00000000 00000000\n60000000 00000000"[1 + endingZeros * 2:]
        elif endingZeros > 0:
            post = "00000000 00000000"[endingZeros * 2:]
    return rawhex[:-1] + post

def construct_code(rawhex, bapo=None, xor=None, chksum=None, ctype=None):
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

    if isFailed == False:
        if rawhex[-1] == " ":
            post = " 00000000"
        else:
            post = "\n60000000 00000000"

        if ctype == "C0":
            pre = "C0000000 {}\n".format("".join(leading_zeros[0]) + numlines)
            post = "4E800020" + post[-9:]
        else:
            if bapo[0] not in ("8", "0") or bapo[1] not in ("0", "1") or int(bapo[2], 16) > 7:
                raise CodetypeError("Invalid bapo '" + bapo[:2] + "'")

            pre = {"8": "C", "0": "D"}.get(bapo[0], "C")
            if bapo[1] == "1":
                pre += "3" + bapo[2:] + " "
            else:
                pre += "2" + bapo[2:] + " "

            if ctype == "C2D2":
                pre += "".join(leading_zeros[0]) + numlines + "\n"
            elif ctype == "0616":
                pre = {"8": "0", "0": "1"}.get(bapo[0], "0")
                if bapo[1] == "1":
                    pre += "7" + bapo[2:] + " "
                else:
                    pre += "6" + bapo[2:] + " "
                pre += "".join(leading_zeros[1]) + numbytes + "\n"
            else:  # ctype == "F2F4"
                if int(numlines, 16) <= 0xFF:
                    pre = "F" + str(int({"D": "2"}.get(pre[0], "0")) + int(pre[1]))
                    if int(numlines, 16) <= 0xF:
                        numlines = "0"+numlines

                    pre += bapo[2:] + " " + "{:02X}".format(int(chksum, 16)) + "{:04X}".format(int(xor, 16)) + numlines + "\n"
                else:
                    raise CodetypeError("Number of lines (" +
                                        numlines + ") must be lower than 0xFF")
        return pre + alignHeader(rawhex, post, ctype, numbytes)
    else:
        return rawhex


def deconstruct_code(codes):
    codetypes = ("06", "07", "16", "17", "C0", "C2", "C3", "D2", "D3", "F2", "F3", "F4", "F5")
    if codes[:2] not in codetypes:
        return (codes, None, None, None, None)

    bapo = None
    xor = None
    chksum = None
    codetype = "C0"

    if codes[:2] != "C0":
        codetype = "C2D2"
        bapo = {"0": "8", "1": "0", "C": "8", "D": "0", "F": "8"}.get(codes[0], "8")
        if codes[1] in ("4", "5"):
            bapo = "0"
        bapo += str(int(codes[1]) % 2) + codes[2:8]

        if codes[0] == "F":
            codetype = "F2F4"
            chksum = codes[9:11]
            xor = codes[11:15]
        elif codes[0] in ("0", "1"):
            codetype = "0616"

    if codes[-17:-9] == "60000000" or codes[-17:] == "4E800020 00000000":
        return (codes[18:-17], bapo, xor, chksum, codetype)
    else:
        return (codes[18:-9], bapo, xor, chksum, codetype)


setup()
