#!/usr/bin/env python3
import os
import ctypes
import sys

# Force load libusb DLL manually
dll_path = os.path.join(os.path.dirname(__file__), "libusb-1.0.dll")
try:
    ctypes.CDLL(dll_path)
except OSError as e:
    raise ImportError(f"Failed to load libusb-1.0.dll manually: {e}")

import usb.core
import usb.util
import time
import usb.backend.libusb1  # Explicitly import the libusb1 backend
import argparse

ESC = b"\x1b"
FS  = b"\x1c"

SEQUENCE_START_BIT   = 0b10000000
SEQUENCE_END_BIT     = 0b01000000
SEQUENCE_LENGTH_BITS = 0b00111111

VENDOR_ID = 0x0801
PRODUCT_ID = 0x0003
HID_PACKET_SIZE = 64
HID_PAYLOAD_SIZE = 63

map_5bits = {   "00001": ["00", "0"],
                "10000": ["01", "1"],
                "01000": ["02", "2"],
                "11001": ["03", "3"],
                "00100": ["04", "4"],
                "10101": ["05", "5"],
                "01101": ["06", "6"],
                "11100": ["07", "7"],
                "00010": ["08", "8"],
                "10011": ["09", "9"],
                "01011": ["0A", ":"],
                "11010": ["0B", ";"],
                "00111": ["0C", "<"],
                "10110": ["0D", "="],
                "01110": ["0E", ">"],
                "11111": ["0F", "?"]
            }

map_7bits = {   "0000001": ["00", " "],
                "1000000": ["01", "!"],
                "0100000": ["02", "\""],
                "1100001": ["03", "#"],
                "0010000": ["04", "$"],
                "1010001": ["05", "%"],
                "0110001": ["06", "&"],
                "1110000": ["07", "'"],
                "0001000": ["08", "("],
                "1001001": ["09", ")"],
                "0101001": ["0A", "*"],
                "1101000": ["0B", "+"],
                "0011001": ["0C", "`"],
                "1011000": ["0D", "-"],
                "0111000": ["0E", "."],
                "1111000": ["0F", "/"],
                "0000100": ["10", "0"],
                "1000101": ["11", "1"],
                "0100101": ["12", "2"],
                "1100100": ["13", "3"],
                "0010101": ["14", "4"],
                "1010100": ["15", "5"],
                "0110100": ["16", "6"],
                "1110101": ["17", "7"],
                "0001101": ["18", "8"],
                "1001100": ["19", "9"],
                "0101100": ["1A", ":"],
                "1101101": ["1B", ";"],
                "0011100": ["1C", "<"],
                "1011101": ["1D", "="],
                "0111101": ["1E", ">"],
                "1111100": ["1F", "?"],
                "0000010": ["20", "@"],
                "1000011": ["21", "A"],
                "0100011": ["22", "B"],
                "1100010": ["23", "C"],
                "0010011": ["24", "D"],
                "1010010": ["25", "E"],
                "0110010": ["26", "F"],
                "1110011": ["27", "G"],
                "0001011": ["28", "H"],
                "1001010": ["29", "I"],
                "0101010": ["2A", "J"],
                "1101011": ["2B", "K"],
                "0011000": ["2C", "L"],
                "1011011": ["2D", "M"],
                "0111011": ["2E", "N"],
                "1111010": ["2F", "O"],
                "0000111": ["30", "P"],
                "1000110": ["31", "Q"],
                "0100110": ["32", "R"],
                "1100111": ["33", "S"],
                "0010110": ["34", "T"],
                "1010111": ["35", "U"],
                "0110111": ["36", "V"],
                "1110110": ["37", "W"],
                "0001110": ["38", "X"],
                "1001111": ["39", "Y"],
                "0101111": ["3A", "Z"],
                "1101110": ["3B", "["],
                "0011111": ["3C", "\\"],
                "1011110": ["3D", "]"],
                "0111110": ["3E", "^"],
                "1111111": ["3F", "_"]
            }

class MSR605X:
    def __init__(self, **kwargs):
        if "idVendor" not in kwargs:
            kwargs["idVendor"] = 0x0801
            kwargs["idProduct"] = 0x0003
            backend = usb.backend.libusb1.get_backend(find_library=lambda x: dll_path)
        self.dev = usb.core.find(backend=backend, **kwargs)
        if self.dev is None:
            raise ValueError("Device not found. Check connection.")
        self.hid_endpoint = None
        self.connect()  # Ensure connect() is called during initialization

    def connect(self):
        """Establish a connection to the MSR605X."""
        if sys.platform.startswith("linux"):
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
        self.dev.set_configuration()
        config = self.dev.get_active_configuration()
        interface = config[(0, 0)]
        self.hid_endpoint = interface.endpoints()[0]

    def close(self):
        usb.util.dispose_resources(self.dev)

    def _make_header(self, start_of_sequence: bool, end_of_sequence: bool, length: int):
        if length < 0 or length > 63:
            raise ValueError("Length must be between 0 and 63")
        header = length
        if start_of_sequence:
            header |= SEQUENCE_START_BIT
        if end_of_sequence:
            header |= SEQUENCE_END_BIT
        return bytes([header])

    def _encapsulate_message(self, message):
        idx = 0
        while idx < len(message):
            payload = message[idx:idx+HID_PAYLOAD_SIZE]
            header = self._make_header(idx == 0, len(message) - idx < HID_PACKET_SIZE, len(payload))
            padding = b"\0" * (HID_PAYLOAD_SIZE - len(payload))
            yield header + payload + padding
            idx += HID_PAYLOAD_SIZE

    def write(self, data: bytes):
        for pkt in self._encapsulate_message(data):
            self.dev.ctrl_transfer(0x21, 9, wValue=0x0300, wIndex=0, data_or_wLength=pkt)

    def read(self, timeout=0.5):
        start_time = time.time()
        result = b''
        while True:
            try:
                pkt = self.hid_endpoint.read(HID_PACKET_SIZE, timeout=int(timeout * 1000))
                if not pkt:
                    if (time.time() - start_time) > timeout:
                        break
                    continue
                header = pkt[0]
                payload_len = header & SEQUENCE_LENGTH_BITS
                payload = bytes(pkt[1:1+payload_len])
                result += payload
                if header & SEQUENCE_END_BIT:
                    break
            except usb.core.USBError as e:
                if hasattr(e, 'errno') and e.errno == 110:
                    break
                raise
        return result

def msr_init():
    try:
        dev = MSR605X()
        print(" [+] device initialisation: OK")
        return dev
    except Exception as e:
        print(" [-] device initialisation: KO", e)
        return False

def msr_reset(dev_ptr):
    try:
        dev_ptr.write(ESC + b"a")
        time.sleep(0.5)
        print(" [+] device reset to initial state: OK")
        result = True
    except Exception as e:
        print(" [-] device reset to initial state: KO", e)
        result = False
    return result

def execute_waitresult(command, dev_ptr, timeout=10):
    if isinstance(command, str):
        command = command.encode()
    dev_ptr.write(ESC + command)
    time.sleep(0.1)
    result = dev_ptr.read(timeout)
    time.sleep(0.5)
    if not result:
        print(" [*] operation timed out")
        return b"", b"", b""
    try:
        pos = result.rindex(ESC)
        status = result[pos+1:pos+2]
        res = result[pos+2:]
        data = result
        return status, res, data
    except Exception as e:
        print(" [*] error parsing result:", e)
        return b"", b"", b""

def set_coercivity(coercivity, dev_ptr):
    if coercivity == 'hico':
        status, _, _ = execute_waitresult(b"x", dev_ptr)
    elif coercivity == 'loco':
        status, _, _ = execute_waitresult(b"y", dev_ptr)
    else:
        print(" [-] set_coercivity() error: invalid value")
        return False
    if status != b"0":
        print(f" [-] set_coercivity() error: {status}")
        return False
    print(" [+] set coercivity: OK")
    return True

def set_bpc(bpc1, bpc2, bpc3, dev_ptr):
    status, result, _ = execute_waitresult(b"o" + bytes([bpc1, bpc2, bpc3]), dev_ptr)
    if status != b"0":
        print(f" [-] set_bpc() error: {status}")
        return False
    print(" [+] set bpc: OK")
    return True

def read_raw_tracks(dev_ptr):
    status, _, data = execute_waitresult(b"m", dev_ptr)
    if status != b"0":
        print(" [*] maybe it is an empty card, or not in the good type: set type iso/raw")
        return b"", b"", b""
    return decode_rawdatablock(data)

def read_iso_tracks(dev_ptr):
    status, _, data = execute_waitresult(b"r", dev_ptr)
    if status != b"0":
        print(" [*] Maybe it is an empty one card")
        return b"", b"", b""
    return decode_isodatablock(data)

def decode_rawdatablock(data):
    if data[0:4] != ESC + b"s" + ESC + b"\x01":
        print(" [-] bad datablock : don't start with", ESC.hex(), b"s", ESC.hex(), b"\x01", data)
        return b"", b"", b""
    try:
        strip1_start = 4
        strip1_len = data[strip1_start]
        strip1_end = strip1_start + 1 + strip1_len
        strip1 = data[strip1_start+1:strip1_end]

        # Find ESC + b"\x02" after strip1
        esc2_pos = data.index(ESC + b"\x02", strip1_end)
        strip2_start = esc2_pos + 2
        strip2_len = data[strip2_start]
        strip2_end = strip2_start + 1 + strip2_len
        strip2 = data[strip2_start+1:strip2_end]

        # Find ESC + b"\x03" after strip2
        esc3_pos = data.index(ESC + b"\x03", strip2_end)
        strip3_start = esc3_pos + 2
        strip3_len = data[strip3_start]
        strip3_end = strip3_start + 1 + strip3_len
        strip3 = data[strip3_start+1:strip3_end]

        if data[strip3_end:] != b"\x3F" + FS:
            print(f" [-] bad datablock : missing 3F 1C at position {strip3_end}", data)
            return b"", b"", b""
        return strip1, strip2, strip3
    except Exception as e:
        print(" [-] Exception in decode_rawdatablock:", e, data)
        return b"", b"", b""

def decode_isodatablock(data):
    if data[0:4] != ESC + b"s" + ESC + b"\x01":
        print(" [-] bad datablock : don't start with 1B 73 1B 01", data)
        return b"", b"", b""
    if data[-4:-2] != b"\x3F" + FS:
        print(" [-] bad datablock : don't end with 3F 1C", data)
        return b"", b"", b""
    strip1_start = 4
    strip1_end = data.index(ESC, strip1_start)
    strip1 = data[strip1_start:strip1_end] if strip1_end != strip1_start else None
    strip2_start = strip1_end+2
    if data[strip1_end:strip2_start] != ESC + b"\x02":
        print(f" [-] bad datablock : missing 1B 02 at position {strip1_end}", data)
        return b"", b"", b""
    strip2_end = data.index(ESC, strip2_start)
    strip2 = data[strip2_start:strip2_end] if strip2_end != strip2_start else None
    strip3_start = strip2_end+2
    if data[strip2_end:strip3_start] != ESC + b"\x03":
        print(f" [-] bad datablock : missing 1B 03 at position {strip2_end}", data)
        return b"", b"", b""
    strip3 = None if data[strip3_start:strip3_start+1] == ESC else data[strip3_start:-4]
    return strip1, strip2, strip3

def write_raw_tracks(t1, t2, t3, dev_ptr):
    data = encode_rawdatablock(t1, t2, t3)
    status, _, _ = execute_waitresult(b"n" + data, dev_ptr)
    if status != b"0":
        print(f" [-] write_raw_tracks() error: {status}")
        return False
    return True

def write_iso_tracks(t1, t2, t3, dev_ptr):
    t1 = t1 or b""
    t2 = t2 or b""
    t3 = t3 or b""
    data = encode_isodatablock(t1, t2, t3)
    status, _, _ = execute_waitresult(b"w" + data, dev_ptr)
    if status != b"0":
        print(" [*] probably too fast, take your time to swipe the card")
        return False
    return True

def encode_rawdatablock(strip1, strip2, strip3):
    return ESC + b"s" + ESC + b"\x01" + bytes([len(strip1)]) + strip1 + ESC + b"\x02" + bytes([len(strip2)]) + strip2 + ESC + b"\x03" + bytes([len(strip3)]) + strip3 + b"\x3F" + FS

def encode_isodatablock(strip1, strip2, strip3):
    return ESC + b"s" + ESC + b"\x01" + strip1 + ESC + b"\x02" + strip2 + ESC + b"\x03" + strip3 + b"\x3F" + FS

def erase_tracks(dev_ptr, t1, t2, t3):
    mask = 0
    if t1: mask |= 1
    if t2: mask |= 2
    if t3: mask |= 4
    status, _, _ = execute_waitresult(b"c" + bytes([mask]), dev_ptr)
    if status != b"0":
        print(f" [-] erase_tracks() error: {status}")
        print(" [-] Not erased.")
        return False
    print(" [+] Erased.")
    return True

def set_leadingzero(track13, track2, dev_ptr):
    status, result, _ = execute_waitresult(b"z" + track13 + track2, dev_ptr)
    if status != b"0":
        print(f" [-] set_leadingzero() error: {status}")

def set_bpi(bpi1, bpi2, bpi3, dev_ptr):
    modes = []
    if bpi1 == "210":
        modes.append(0xA1)
    elif bpi1 == "75":
        modes.append(0xA0)
    if bpi2 == "210":
        modes.append(0xD2)
    elif bpi2 == "75":
        modes.append(0x4B)
    if bpi3 == "210":
        modes.append(0xC1)
    elif bpi3 == "75":
        modes.append(0xC0)
    for m in modes:
        status, result, _ = execute_waitresult(b"b" + bytes([m]), dev_ptr)
        if status != b"0":
            print(f" [-] set_bpi() error: {status} for {hex(m)}")

def get_device_model(dev_ptr):
    _, _, result = execute_waitresult(b"t", dev_ptr)
    return result[1:]

def get_firmware_version(dev_ptr):
    _, _, result = execute_waitresult(b"v", dev_ptr)
    return result[1:]

def get_hico_loco_status(dev_ptr):
    dev_ptr.write(ESC + b"d")
    time.sleep(0.1)
    result = dev_ptr.read(1)
    if result == b'H':
        return 'hico'
    elif result == b'L':
        return 'loco'
    else:
        return ''

def do_ram_test(dev_ptr):
    dev_ptr.write(ESC + b"\x86")
    time.sleep(0.1)
    result = dev_ptr.read(1)
    if result == b"0":
        return 'OK'
    else:
        return 'KO'

def do_communication_test(dev_ptr):
    dev_ptr.write(ESC + b"e")
    time.sleep(0.1)
    result = dev_ptr.read(1)
    if result == b"y":
        return 'OK'
    else:
        return 'KO'

def do_sensor_test(dev_ptr):
    status, _, _ = execute_waitresult(b"\x86", dev_ptr)
    if status != b"0":
        print(f" [-] do_sensor_test() error: {status}")
        return False
    print(" [+] the card sensing circuit works properly")
    return True

def play_all_led_off(dev_ptr):
    dev_ptr.write(ESC + b"\x81")
    print(" [+] all led off")

def play_all_led_on(dev_ptr):
    dev_ptr.write(ESC + b"\x82")
    print(" [+] all led on")

def play_green_led_on(dev_ptr):
    dev_ptr.write(ESC + b"\x83")
    print(" [+] green led on")

def play_yellow_led_on(dev_ptr):
    dev_ptr.write(ESC + b"\x84")
    print(" [+] yellow led on")

def play_red_led_on(dev_ptr):
    dev_ptr.write(ESC + b"\x85")
    print(" [+] red led on")
