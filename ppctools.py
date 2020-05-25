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

    output = subprocess.Popen([eabi["as"], "-a32", "-mbig", "-mregnames", "-mgekko", "-o",
                               tmpdir + "src1.o", txtfile], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).communicate()
    time.sleep(.25)

    if output[1]:
        errormsg = str(output[1], encoding="utf-8")
        errormsg = errormsg.replace(txtfile + ":", "")
        errormsg = errormsg.replace(" Assem", "Assem", 1)
        raise RuntimeError(errormsg)

    subprocess.Popen([eabi["ld"], "-Ttext", "0x80000000", "-o",
                      tmpdir+"src2.o", tmpdir+"src1.o"], stderr=subprocess.PIPE)
    time.sleep(.25)
    subprocess.Popen([eabi["objcopy"], "-O", "binary",
                      tmpdir + "src2.o", binfile], stderr=subprocess.PIPE)
    time.sleep(.25)

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
    branch_label = ".loc_0x{}:"
    unsigned_instructions = ["lis", "ori", "oris", "xori", "xoris",
                             "andi.", "andis."]
    nonhex_instructions = ["rlwinm", "rlwinm.", "rlwnm" "rlwnm."
                           "rlwimi", "rlwimi."]

    #Set default first label
    textoutput.append(branch_label.format("0"))

    for ppc in re.findall(ppc_pattern, output):
        if ppc[2] == "b":
            SIMM = "{:07X}".format(int(ppc[1][1:], 16) & 0x3FFFFFD)
        else:
            SIMM = "{:04X}".format(int(ppc[1][4:], 16) & 0xFFFD)

        #Check for a branch instruction
        if ppc[2].startswith("b") and "0x" in ppc[3]:
            #Parse branch instruction to create a label
            label, positive = assert_label(ppc, branch_label, SIMM)
            if label and label not in labels and positive == True:
                labels.append(label)
            #We need to check for register crap
            if positive == True:
                if "," in ppc[3]:
                    textoutput.append("  " + ppc[2] + " " + re.sub(r"(?<=,| )(?:0x| +|)[a-fA-F0-9]+", " " + label[:-1], ppc[3]))
                else:
                    textoutput.append("  " + ppc[2] + " " + label[:-1])
            else:
                if "," in ppc[3]:
                    textoutput.append("  " + ppc[2] + " " + re.sub(r"(?<=,| )(?:0x| +|)[a-fA-F0-9]+", " " + hex(sign_extend(int(SIMM, 16), len(SIMM) - 1)), ppc[3]))
                else:
                    textoutput.append("  " + ppc[2] + " " + hex(sign_extend(int(SIMM, 16), len(SIMM) - 1)))
        else:
            #Set up cleaner format
            values = ppc[3]
            if ppc[2] not in nonhex_instructions:
                for match in re.findall(r"(?<=,)(?<!r|c)[-\d]+(?!x)(?:\(|)", ppc[3]):
                    if "(" in match and ppc[2] not in unsigned_instructions:
                        match = "0x{:X}(".format(int(match[:-1], 10))
                        match = re.sub(r"0x-", "-0x", match)
                    elif ppc[2] not in unsigned_instructions:
                        match = "0x{:X}".format(int(match, 10))
                        match = re.sub(r"0x-", "-0x", match)
                    else:
                        print("Unsigned Instruction")
                        match = "0x{:X}".format(int(match, 10))
                        match = re.sub(r"0x-", "0x", match)
                    values = re.sub(r"(?<=,)(?<!r|c)[-\d]+(?!x)(?:\(|)", match, ppc[3], count=1)
                values = re.sub(",", ", ", values)
            textoutput.append("  " + ppc[2] + " " + values)

    #Sort all labels
    label_set = sorted_alphanumeric(set(labels))
    #Set up labels in text output
    for i, label in enumerate(label_set, start=1):
        labeloffset = re.findall("(?:[0x-])([a-fA-F0-9]+)", label)
        labelIndex = int(int(labeloffset[0], 16) / 4) + i
        if labelIndex < len(textoutput) and labelIndex >= 0:
            textoutput.insert(labelIndex, "\n" + label)
        elif labelIndex >= 0:
            textoutput.insert(len(textoutput), "\n" + label)
        else:
            textoutput.insert(0, "\n" + label)

    # Return the disassembled opcodes
    return " ".join("\n".join(textoutput).split("\t"))

def sorted_alphanumeric(l): 
    """ Sort the given iterable in the way that humans expect.""" 
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(l, key = alphanum_key)

def sign_extend(value, bytesize):
    """ Sign extend an int value """
    if bytesize == 0:
        return value
    if bytesize > 4:
        if value & (0x3 << ((bytesize) * 4)):
            return value - (0x4 << (bytesize * 4))
        else:
            return value
    else:
        if value & (0x8 << ((bytesize - 1) * 4)):
            return value - (0x10 << (bytesize * 4))
        else:
            return value
    

def assert_label(ppc_list, label, SIMM):
    SIMM = sign_extend(int(SIMM, 16), len(SIMM) - 1)
    positive = True
    #Check if it branches before the start
    if (int(ppc_list[0], 16) + SIMM) < 0:
        positive = False
    return [label.format("{:X}".format(int(ppc_list[0], 16) + SIMM)).replace("-", ""), positive]

def construct_code(rawhex, bapo=None, xor=None, chksum=None, ctype=None):
    if ctype is None:
        return rawhex

    numlines = ("{:X}".format(len(rawhex.split("\n"))))
    leading_zeros = ["0" * (8 - len(numlines))]

    try:
        isFailed = False
        int(rawhex.replace("\n", "").replace(" ", ""), 16)
    except ValueError:
        isFailed = True

    if isFailed == False:
        if rawhex[-1] == " ":
            post = "00000000"
        else:
            post = "60000000 00000000"

        if ctype == "C0":
            pre = "C0000000 %s%s\n" % ("".join(leading_zeros), numlines)
            post = "4E800020" + post[8:]
            return pre + rawhex + post
        else:
            if bapo[0] not in ("8", "0") or bapo[1] not in ("0", "1"):
                raise CodetypeError("Invalid bapo '" + bapo[:2] + "'")

            pre = {"8": "C", "0": "D"}.get(bapo[0], "C")
            if bapo[1] == "1":
                pre += "3" + bapo[2:] + " "
            else:
                pre += "2" + bapo[2:] + " "

            if ctype == "C2D2":
                pre += "".join(leading_zeros) + numlines + "\n"
                return pre + rawhex + post
            else:  # ctype == "F2F4"
                if int(numlines, 16) <= 0xFF:
                    pre = "F" + str(int({"D": "2"}.get(pre[0], "0")) + int(pre[1]))
                    if int(numlines, 16) <= 0xF:
                        numlines = "0"+numlines

                    pre += bapo[2:] + " " + chksum + xor + numlines + "\n"
                    return pre + rawhex + post
                else:
                    raise CodetypeError("Number of lines (" +
                                        numlines + ") must be lower than 0xFF")
    else:
        return rawhex


def deconstruct_code(codes):
    codetypes = ("C0", "C2", "C3", "D2", "D3", "F2", "F3", "F4", "F5")
    if codes[:2] not in codetypes:
        return (codes, None, None, None, None)

    bapo = None
    xor = None
    chksum = None
    codetype = "C0"

    if codes[:2] != "C0":
        codetype = "C2D2"
        bapo = {"C": "8", "D": "0", "F": "8"}.get(codes[0], "8")
        if codes[1] in ("4", "5"):
            bapo = "0"
        bapo += str(int(codes[1]) % 2) + codes[2:8]

        if codes[0] == "F":
            codetype = "F2F4"
            chksum = codes[9:11]
            xor = codes[11:15]

    if codes[-17:-9] == "60000000" or codes[-17:] == "4E800020 00000000":
        return (codes[18:-17], bapo, xor, chksum, codetype)
    else:
        return (codes[18:-9], bapo, xor, chksum, codetype)


setup()
