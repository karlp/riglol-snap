#!/usr/bin/python3
"""
Grab a "screenshot" from a rigol 1000D/E series.
Uses an undocumented :lcd:data? method discovered on
https://www.improwis.com/projects/sw_USBTMC_RigolScopeWifi/
"""
import argparse
import datetime
import pyvisa
from PIL import Image as im


def get_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-f", "--file", help="output file name, default will be auto timestamped")
    options = parser.parse_args()
    return options


def new_style(opts):
    # lol, just dump the screen via a private undocumented command.
    # Thank you: https://www.improwis.com/projects/sw_USBTMC_RigolScopeWifi/
    rm = pyvisa.ResourceManager()
    # We can pre-filter, but somehow can't only look at USB?!
    riglols = rm.list_resources("USB?*6833::1416::?*INSTR")
    if len(riglols) == 0:
        print("No suitable Rigol devices found.")
        return
    # just work with dev 1
    selected = riglols[0]
    dev_serial = selected.split("::")[3].rstrip("\x00")
    print(f"Opening device: {dev_serial}", end="")
    dev: pyvisa.resources.MessageBasedResource = rm.open_resource(selected)

    # leave local control
    def k_before_close():
        dev.write(":KEY:force")
    dev.before_close = k_before_close

    # Apparently newer firmware may include the header, and then you wouldn't need most of this...
    # _could_ use the IDN result (which has firmware) but would need more test data... riiiight
    # Despite starting with a "#800074880" block, pyvisa ieee decoding fails to read this
    # without changing chunk size, as per their own FAQ.
    rawlcd = dev.query_binary_values(":lcd:data?", datatype='B', chunk_size=100000)
    # Simple doing it raw works too...
    #dev.write(":lcd:data?")
    #rawlcd = dev.read_raw(74880+10)[10:]
    #  (raw 320x234 2:3:3 LCD dump, 74880 bytes)

    # expand everything from 2:3:3 to 8:8:8 pixels....
    # um, this pains me, there's got to be a better way...
    out = []
    for x in rawlcd:
        out.append(x & 0xc0)
        out.append((x & 0x38) << 2)
        out.append((x & 0x7) << 5)
    dat = im.frombytes("RGB", (320, 234), bytes(out))
    dstr = datetime.datetime.now().strftime("%Y%m%dT%H%M%S.%f")

    fname = getattr(opts, "file", f"snap-riglol-{dstr}.png")
    dat.save(fname)
    print(f" -> saved to {fname}")


if __name__ == "__main__":
    opts = get_args()
    new_style(opts)

