#!/usr/bin/env python3
#
# Electron Cash - lightweight Bitcoin client
# Copyright (C) 2019 Axel Gembe <derago@gmail.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# A module, that, given an image (buffer), finds and decodes a QR code in it.

import re
from .qr_decoders import SpecterPsbtDecoder, URPsbtDecoder, SpecterWalletQrDecoder


def get_psbt_decoder(s):
        if re.search("^UR:CRYPTO-PSBT/", s, re.IGNORECASE):
            return URPsbtDecoder()
        if re.search(r'^p(\d+)of(\d+) ', s, re.IGNORECASE): #
            if re.search(r'^p(\d+)of(\d+) ([A-Za-z0-9+\/=]+$)', s, re.IGNORECASE): #must be base64 characters only in segment
                return SpecterPsbtDecoder()
            else:
                return SpecterWalletQrDecoder()
        else:
            return None

