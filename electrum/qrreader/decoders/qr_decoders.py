#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@gitorious
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


import base64
import re
import json
from electrum.qrreader.decoders.ur2.ur_decoder import URDecoder
from cbor2 import loads as cbor_loads


class BaseAnimatedQrDecoder():
    def __init__(self):
        super().__init__()
        self.segments = []
        self.total_segments = None
        self.collected_segments = 0
        self.complete = False

    def is_complete(self) -> bool:
        return self.complete

    def current_segment_num(self, segment) -> int:
        raise Exception("Not implemented in child class")

    def total_segment_nums(self, segment) -> int:
        raise Exception("Not implemented in child class")

    def parse_segment(self, segment) -> str:
        raise Exception("Not implemented in child class")
    
    def receive_part(self, segment):
        if self.total_segments == None:
            self.total_segments = self.total_segment_nums(segment)
            self.segments = [None] * self.total_segments
        elif self.total_segments != self.total_segment_nums(segment):
            raise Exception('Segment total changed unexpectedly')

        if self.segments[self.current_segment_num(segment) - 1] == None:
            self.segments[self.current_segment_num(segment) - 1] = self.parse_segment(segment)
            self.collected_segments += 1
            if self.total_segments == self.collected_segments:
                self.complete = True


class SpecterPsbtDecoder(BaseAnimatedQrDecoder):

    def get_base64_data(self) -> str:
        base64 = "".join(self.segments)
        return base64

    def current_segment_num(self, segment) -> int:
        if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
            return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(1))


    def total_segment_nums(self, segment) -> int:
        if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
            return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(2))


    def parse_segment(self, segment) -> str:
        return segment.split(" ")[-1].strip()

class URPsbtDecoder(URDecoder):

    def get_base64_data(self) -> str:
        raw_cbor = super().result_message().cbor
        cbor_obj = cbor_loads(raw_cbor)
        return base64.b64encode(cbor_obj).decode("utf-8")

class SpecterWalletQrDecoder(BaseAnimatedQrDecoder):
    """
        Decodes animated frames to get a wallet descriptor from Specter Desktop
    """
    def validate_json(self) -> str:
        try:
            j = "".join(self.segments)
            data = json.loads(j)
            print("got json data\n")
            print(data)
            print("\n")
        except json.decoder.JSONDecodeError:
            return False
        return True


    def is_valid(self):
        if self.validate_json():
            j = "".join(self.segments)
            data = json.loads(j)
            if "descriptor" in data:
                return True
            return False


    def get_wallet_descriptor(self) -> str:
        if self.is_valid:
            j = "".join(self.segments)
            data = json.loads(j)
            return data['descriptor']
        return None


    def is_complete(self) -> bool:
        j = "".join(self.segments)
        print("got raw text: " + j)
        data = json.loads(j)
        print("got json data\n")
        print(data)
        print("\n")
        return self.complete# and self.is_valid()
        return self.complete and self.is_valid()


    def current_segment_num(self, segment) -> int:
        if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
            return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(1))
        else:
            return 1


    def total_segment_nums(self, segment) -> int:
        if re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE) != None:
            return int(re.search(r'^p(\d+)of(\d+) ', segment, re.IGNORECASE).group(2))
        else:
            return 1


    def parse_segment(self, segment) -> str:
        try:
            return re.search(r'^p(\d+)of(\d+) (.+$)', segment, re.IGNORECASE).group(3)
        except:
            return segment


