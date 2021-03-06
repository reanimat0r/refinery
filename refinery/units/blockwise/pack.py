#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

from . import arg, BlockTransformation
from ...lib.argformats import number
from ...lib.patterns import formats
from ..encoding.base import base as base_unit


class pack(BlockTransformation):
    """
    Scans the input data for numeric constants and packs them into a binary
    format. This is useful to convert the textual representation of an array of
    numbers into its binary form. For example, `123,34,256,12,1,234` would be
    transformed into the byte sequence `7B22000C01EA`, where `256` was wrapped
    and packed as a null byte because the default block size is one byte. If
    the above sequence would be packed with options -EB2, the result would be
    equal to `007B00220100000C000100EA` in hexadecimal.
    """

    def __init__(self,
        base: arg(type=number[2:36], help=(
            'Find only numbers in given base. Default of 0 means that '
            'common expressions for hexadecimal, octal and binary are '
            'accepted.')) = 0,
        hexdump : arg.switch('-x', help='Parse only pairs of hexadecimal digits surrounded by whitespace.') = False,
        prefix  : arg.switch('-r', help='Add numeric prefixes like 0x, 0b, and 0o in reverse mode.') = False,
        bigendian=False, blocksize=1
    ):
        super().__init__(
            base=0x10 if hexdump else base,
            hexdump=hexdump,
            prefix=prefix,
            bigendian=bigendian,
            blocksize=blocksize
        )

    @property
    def bytestream(self):
        # never alow bytes to be left unchunked
        return False

    def reverse(self, data):
        base = self.args.base or 10
        prefix = B''

        self.log_debug(F'using base {base:d}')

        if self.args.prefix:
            prefix = {
                0x02: b'0b',
                0x08: b'0o',
                0x10: b'0x'
            }.get(base, B'')

        converter = base_unit(base, self.args.bigendian)

        for n in self.chunk(data, raw=True):
            yield prefix + converter.reverse(n)

    def process(self, data):
        if self.args.hexdump:
            pattern = re.compile(
                BR'(?:\W|\s|^)(?:0x)?([0-9a-f]{%i})h?(?=\s|$)' % (self.args.blocksize * 2),
                re.IGNORECASE
            )
        elif self.args.base == 0:
            pattern = formats.integer
        elif self.args.base <= 10:
            pattern = re.compile(B'[-+]?[0-%d]{1,64}' % (self.args.base - 1))
        else:
            pattern = re.compile(B'[-+]?[0-9a-%c]{1,20}' % (0x57 + self.args.base), re.IGNORECASE)

        items = pattern.findall(data)
        items = [int(n, self.args.base) & self.fmask for n in items]
        return self.unchunk(items)
