#!/usr/bin/env python3
import sys, os
import datetime
from os.path import isfile, join
from os import listdir
import time
from colorama import Fore, Back

from msr605_drv import (
    msr_init, msr_reset, set_coercivity, set_bpc, set_bpi,
    read_iso_tracks, read_raw_tracks, write_iso_tracks, write_raw_tracks, erase_tracks,
    get_firmware_version, get_device_model, play_all_led_on, play_all_led_off,
    play_green_led_on, play_yellow_led_on, play_red_led_on
)
import msr605x

# auto-completion
cmdList = [ 'autosave ',
            'bpc ',
            'clear', 
            'bulk_compare',
            'bulk_copy',
            'bulk_erase',
            'bulk_read',
            'bulk_write',
            'compare', 
            'copy', 
            'erase', 
            'exit', 
            'help', 
            'hico',
            'iso',
            'led',
            'loco',
            'mode ',
            'off',
            'on',
            'play',
            'raw',
            'read', 
            'reset',
            'save',
            'set ',
            'settings',
            'type ',
            'write', 
            'quit',
            'pan'  # Added PAN command
]

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

def completer(text, state):
    options = [x for x in cmdList if x.startswith(text)]
    try:
        return options[state]
    except IndexError:
        return None

def get_hex_value(strip):
    res = ""
    for i in strip:
        val = i[2:]
        if len(val) == 1:
            val = '0'+val
        res += val
    return res

def help_menu():
    print("="*60)
    print(" Play with MSR605 **\\(^.^)//**")
    print(" Magnetic Swipe Card Reader/Writer")
    print("="*23+"COMMAND LINE"+"="*25)
    print(' -d (ignored for HID devices)')
    print(' -t <iso/raw>\t\t type')
    print(' -m <hico/loco>\t\t mode')
    print("="*23+"GENERAL"+"="*30)
    print(" ?/help\t\t\t display this help")
    print(" quit/exit\t\t quit the program")
    print(" clear\t\t\t clear the screen")
    print(" settings\t\t display current settings")
    print(" reset\t\t\t reset to default config")
    print("="*23+"ACTIONS"+"="*30)
    print(" compare/bulk_compare")
    print(" copy/bulk_copy")
    print(" erase <1,2,3,12,13,23,123>")
    print(" read/bulk_read")
    print(" save")
    print(" write/bulk_write")
    print(" play <g,y,r,all> led <on,off>")
    print("="*23+"SETTINGS"+"="*29)
    print(" set mode <hico,loco>")
    print(" set type <iso,raw>")
    print(" set autosave <on,off>")
    print(" set bpc <777,456,...>\t not working properly (default: 888)")
    print(" set bpi <1,2,3,all> <210,75>")
    print("="*23+"PAN GENERATION"+"="*25)
    print(" pan random <prefix> <count> <file>")
    print("   Generate <count> random valid PANs with the given prefix and save to <file>.")
    print("   Example: pan random 400000 10 pans.csv")
    print(" pan seq <prefix> <fixed4digits> <file>")
    print("   Generate all valid PANs with the given prefix and fixed 4 digits, save to <file>.")
    print("   Example: pan seq 400000 1234 pans.csv")
    print("")
    print("  (You can also use --pan random:<prefix>:<count> or --pan seq:<prefix>:<fixed4digits> as command line arguments.)")
    print("="*60)

def savedata(filename, folder, data):
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder)
        timestamp = str(datetime.datetime.now()).replace(' ', '_')
        try:
            with open(os.path.join(folder, filename+'_'+timestamp),'w') as fp:
                fp.write(data)
        except Exception as e:
            print(str(e))
        result = True
    except Exception:
        result = False

    if result:
        print(f" [+] Saved to {os.path.join(folder, filename+'_'+timestamp)}")
    else:
        print(" [-] Error during saving")

def verifyEmptyTrack(t1,t2,t3):
    if t1 is None:
        t1 = ''
    if t2 is None:
        t2 = ''
    if t3 is None:
        t3 = ''
    t1,t2,t3 = removeNullByteAtTheEnd(t1,t2,t3)
    return t1,t2,t3

def decodeIso(t1,t2,t3,encode,num_bits=7):
    t1_new = ""
    t2_new = ""
    t3_new = ""
    if num_bits == 7:
        for char in t1:
            for k, v in map_7bits.items():
                if ((char == v[1]) and (encode == 'bin')):
                    t1_new += k
                if ((char == v[1]) and (encode == 'hex')):
                    t1_new += v[0]
        for char in t2:
            for k, v in map_7bits.items():
                if ((char == v[1]) and (encode == 'bin')):
                    t2_new += k
                if ((char == v[1]) and (encode == 'hex')):
                    t2_new += v[0]
        for char in t3:
            for k, v in map_7bits.items():
                if ((char == v[1]) and (encode == 'bin')):
                    t3_new += k
                if ((char == v[1]) and (encode == 'hex')):
                    t3_new += v[0]
    return t1_new,t2_new,t3_new

def removeNullByteAtTheEnd(track1,track2,track3):
    if track1 and track1[-1:] == "\x00":
        track1 = track1[:-1]
    if track2 and track2[-1:] == "\x00":
        track2 = track2[:-1]
    if track3 and track3[-1:] == "\x00":
        track3 = track3[:-1]
    return track1,track2,track3

def printTracks(track1, track2, track3):
    if msr605x.track_type == 'raw':
        print(Fore.GREEN+" [1-binary]: "+Fore.RESET+get_hex_value(map(bin,bytearray(track1.encode() if isinstance(track1, str) else track1))))
        print(Fore.GREEN+" [2-binary]: "+Fore.RESET+get_hex_value(map(bin,bytearray(track2.encode() if isinstance(track2, str) else track2))))
        print(Fore.GREEN+" [3-binary]: "+Fore.RESET+get_hex_value(map(bin,bytearray(track3.encode() if isinstance(track3, str) else track3))))
        print("")
        print(Fore.GREEN+" [1-hexa]: "+Fore.RESET+get_hex_value(map(hex,bytearray(track1.encode() if isinstance(track1, str) else track1))))
        print(Fore.GREEN+" [2-hexa]: "+Fore.RESET+get_hex_value(map(hex,bytearray(track2.encode() if isinstance(track2, str) else track2))))
        print(Fore.GREEN+" [3-hexa]: "+Fore.RESET+get_hex_value(map(hex,bytearray(track3.encode() if isinstance(track3, str) else track3))))
        print("")
        print(Fore.GREEN+" [1-ascii]: "+Fore.RESET+str(track1))
        print(Fore.GREEN+" [2-ascii]: "+Fore.RESET+str(track2))
        print(Fore.GREEN+" [3-ascii]: "+Fore.RESET+str(track3))
    if msr605x.track_type == 'iso':
        track1_b,track2_b,track3_b = decodeIso(track1,track2,track3,'bin')
        print(Fore.GREEN+" [1-binary]: "+Fore.RESET+track1_b)
        print(Fore.GREEN+" [2-binary]: "+Fore.RESET+track2_b)
        print(Fore.GREEN+" [3-binary]: "+Fore.RESET+track3_b)
        print("")
        track1_h,track2_h,track3_h = decodeIso(track1,track2,track3,'hex')
        print(Fore.GREEN+" [1-7bits]: "+Fore.RESET+track1_h)
        print(Fore.GREEN+" [2-7bits]: "+Fore.RESET+track2_h)
        print(Fore.GREEN+" [3-7bits]: "+Fore.RESET+track3_h)
        print("")
        print(Fore.GREEN+" [1-ascii]: "+Fore.RESET+str(track1))
        print(Fore.GREEN+" [2-ascii]: "+Fore.RESET+str(track2))
        print(Fore.GREEN+" [3-ascii]: "+Fore.RESET+str(track3))

def execute(cmd_tokens, dev_ptr):
    if len(cmd_tokens)==0:
        return False

    # SETTINGS
    if cmd_tokens[0] == 'settings':
        model = get_device_model(dev_ptr)
        firmware = get_firmware_version(dev_ptr)
        i = 60
        print("="*i)
        print(' write mode: '+msr605x.mode)
        print(' track type: '+msr605x.track_type)
        print(' bpc1: '+msr605x.bpc[0]+"\t bpc2: "+msr605x.bpc[1]+"\t bpc3: "+msr605x.bpc[2])
        print(' bpi1: '+msr605x.bpi[0]+"\t bpi2: "+msr605x.bpi[1]+"\t bpi3: "+msr605x.bpi[2])
        print(' autosave: '+ str(msr605x.autoSave))
        print("="*i)
        print(' device model: '+str(model))
        print(' firmware version: '+str(firmware))
        print("="*i)
        return True

    if ((cmd_tokens[0] == 'set') and (len(cmd_tokens)>2)):
        if cmd_tokens[1] == 'mode':
            if cmd_tokens[2] == 'hico':
                msr605x.mode = 'hico'
                set_coercivity('hico',dev_ptr)
            elif cmd_tokens[2] == 'loco':
                msr605x.mode = 'loco'
                set_coercivity('loco',dev_ptr)
            else:
                print(' [*] this mode does not exist')
                print(' [*] try: hico or loco')
        elif cmd_tokens[1] == 'type':
            if cmd_tokens[2] == 'iso':
                msr605x.track_type = 'iso'
                print(' [+] type iso: OK')
            elif cmd_tokens[2] == 'raw':
                msr605x.track_type = 'raw'
                print(' [+] type raw: OK')
            else:    
                print(' [*] this track type does not exist')
                print(' [*] try: raw or iso')
        elif cmd_tokens[1] == 'bpc':
            bpc_value = cmd_tokens[2]
            msr605x.bpc[0] = bpc_value[0]
            msr605x.bpc[1] = bpc_value[1]
            msr605x.bpc[2] = bpc_value[2]
            set_bpc(int(msr605x.bpc[0]), int(msr605x.bpc[1]), int(msr605x.bpc[2]), dev_ptr)
            print(' [+] bpc '+cmd_tokens[2]+": OK")
        elif cmd_tokens[1] == "bpi":
            if cmd_tokens[2] == "1":
                msr605x.bpi[0] = cmd_tokens[3]
            elif cmd_tokens[2] == "2":
                msr605x.bpi[1] = cmd_tokens[3]
            elif cmd_tokens[2] == "3":
                msr605x.bpi[2] = cmd_tokens[3]
            elif cmd_tokens[2] == "all":
                msr605x.bpi[0] = cmd_tokens[3]
                msr605x.bpi[1] = cmd_tokens[3]
                msr605x.bpi[2] = cmd_tokens[3]
            else:
                print(" [*] usage: set bpi <1,2,3,all> <210,75>")
            set_bpi(msr605x.bpi[0], msr605x.bpi[1], msr605x.bpi[2], dev_ptr)
            print(" [+] bpi to track "+cmd_tokens[2]+" set to "+cmd_tokens[3]+": OK")
        elif cmd_tokens[1] == 'autosave':
            if cmd_tokens[2] == "on":
                msr605x.autoSave = True
                print(' [+] autosave: on')
            elif cmd_tokens[2] == "off":
                msr605x.autoSave = False
                print(' [+] autosave: off')
        else:
            print(" [-] use the help menu, please")
        return True

    # HELP
    if (cmd_tokens[0] == '?' or cmd_tokens[0]=='help'):
        help_menu()
        return True

    # CLEAR
    if cmd_tokens[0] == 'clear':
        os.system("cls" if os.name == "nt" else "clear")
        return True

    # QUIT
    if (cmd_tokens[0]=="quit" or cmd_tokens[0]=="exit"):
        sys.exit(1)

    # COMPARE
    if cmd_tokens[0] == 'compare':
        print(" [*] swipe card to read")
        if msr605x.track_type == 'iso':
            t1, t2, t3 = read_iso_tracks(dev_ptr)
        if msr605x.track_type == 'raw':
            t1, t2, t3 = read_raw_tracks(dev_ptr)
        t1,t2,t3 = verifyEmptyTrack(t1,t2,t3) 
        printTracks(t1,t2,t3)
        print(" [*] swipe card to compare")
        if msr605x.track_type == 'iso':
            b1, b2, b3 = read_iso_tracks(dev_ptr)
        if msr605x.track_type == 'raw':
            b1, b2, b3 = read_raw_tracks(dev_ptr)
        if b1 == t1 and b2 == t2 and b3 == t3:
            print(" [+] Compare OK")
        else:
            b1,b2,b3 = verifyEmptyTrack(b1,b2,b3) 
            printTracks(b1,b2,b3)
            print(" [-] Compare FAILED")
        return True

    # BULK COMPARE
    if cmd_tokens[0] == 'bulk_compare':
        print(" [*] swipe card to read")
        if msr605x.track_type == 'iso':
            t1, t2, t3 = read_iso_tracks(dev_ptr)
        if msr605x.track_type == 'raw':
            t1, t2, t3 = read_raw_tracks(dev_ptr)
        t1,t2,t3 = verifyEmptyTrack(t1,t2,t3) 
        printTracks(t1,t2,t3)
        while True:
            print(" [*] swipe card to compare")
            try:
                if msr605x.track_type == 'iso':
                    b1, b2, b3 = read_iso_tracks(dev_ptr)
                if msr605x.track_type == 'raw':
                    b1, b2, b3 = read_raw_tracks(dev_ptr)
            except KeyboardInterrupt:
                break
            if b1 == t1 and b2 == t2 and b3 == t3:
                print(" [+] Compare OK")
            else:
                b1,b2,b3 = verifyEmptyTrack(b1,b2,b3) 
                printTracks(b1,b2,b3)
                print(" [-] Compare FAILED")
        return True 

    # READ
    if cmd_tokens[0] == 'read':
        print(" [*] swipe card to read")
        if msr605x.track_type == 'iso':
            t1, t2, t3 = read_iso_tracks(dev_ptr)
        if msr605x.track_type == 'raw':
            t1, t2, t3 = read_raw_tracks(dev_ptr)
        t1,t2,t3 = verifyEmptyTrack(t1,t2,t3) 
        printTracks(t1,t2,t3)
        saveItToFile = f'track1:{t1}\ntrack2:{t2}\ntrack3:{t3}\n'
        if msr605x.autoSave:
            filename = 'autosave'
            savedata(filename, os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + '/../autosave'), saveItToFile)
        msr605x.Save = saveItToFile
        return True

    # BULK READ
    if cmd_tokens[0] == 'bulk_read':
        var_msr605_drv = True
        while var_msr605_drv:
            print(" [*] swipe card to read")
            if msr605x.track_type == 'iso':
                t1, t2, t3 = read_iso_tracks(dev_ptr)
            if msr605x.track_type == 'raw':
                t1, t2, t3 = read_raw_tracks(dev_ptr)
            t1,t2,t3 = verifyEmptyTrack(t1,t2,t3) 
            printTracks(t1,t2,t3)
            saveItToFile = f'track1:{t1}\ntrack2:{t2}\ntrack3:{t3}\n'
            if msr605x.autoSave:
                filename = 'autosave'
                savedata(filename, './autosave', saveItToFile)
            next_ = input(" continue? [Yes/no] ")
            if next_.lower() in ("y", "yes"):
                var_msr605_drv = True
            else:
                var_msr605_drv = False
        return True

    # ERASE
    if cmd_tokens[0] == 'erase':
        print(" [*] swipe card to erase all tracks")
        tracks = cmd_tokens[1] if len(cmd_tokens) > 1 else "123"
        t1 = "1" in tracks
        t2 = "2" in tracks
        t3 = "3" in tracks
        erase_tracks(dev_ptr, t1, t2, t3)
        return True

    # COPY
    if cmd_tokens[0] == 'copy':
        print(" [*] swipe card to read")
        if msr605x.track_type == 'iso':
            t1, t2, t3 = read_iso_tracks(dev_ptr)
        if msr605x.track_type == 'raw':
            print(' [-] cannot copy in raw mode yet, please use: set type iso')
            return True
        t1,t2,t3 = verifyEmptyTrack(t1,t2,t3) 
        printTracks(t1,t2,t3)
        print(" [*] swipe card to write, Ctrl+C to cancel")
        # remove start/end sentinels
        if t1: t1 = t1[1:-1]
        if t2: t2 = t2[1:-1]
        if t3: t3 = t3[1:-1]
        res = write_iso_tracks(t1,t2,t3,dev_ptr)
        if res:
            print(" [+] Written.")
        else:
            print(" [-] Not written")
        return True

    # BULK COPY
    if cmd_tokens[0] == 'bulk_copy':
        print(" [*] swipe card to read, Ctrl+C to cancel")
        if msr605x.track_type == 'iso':
            t1, t2, t3 = msr605_drv.read_iso_tracks(dev_ptr)
        if msr605x.track_type == 'raw':
            print(' [-] cannot copy in raw mode yet, please use: set type iso')
            return True
        t1,t2,t3 = verifyEmptyTrack(t1,t2,t3) 
        printTracks(t1,t2,t3)
        if t1: t1 = t1[1:-1]
        if t2: t2 = t2[1:-1]
        if t3: t3 = t3[1:-1]
        var_msr605_drv = True
        while var_msr605_drv:
            try:
                print(" [*] swipe card to write")
                res = msr605_drv.write_iso_tracks(t1,t2,t3,dev_ptr)
                if res:
                    print(" [+] Written.")
                else:
                    print(" [-] Not written")
            except Exception as e:
                print(" [-] Failed. Error:", e)
            next_ = input(" [*] continue? [Yes/no] ")
            if next_.lower() in ("y", "yes"):
                var_msr605_drv = True
            else:
                var_msr605_drv = False
        return True

    # WRITE
    if cmd_tokens[0] == 'write':
        print(" [*] Input your data. Enter for not writing to a track.")
        t1 = input(" Track 1: ").strip()
        t2 = input(" Track 2: ").strip()
        t3 = input(" Track 3: ").strip()
        print(" [*] swipe card to write")
        if msr605x.track_type == 'iso':
            res = msr605_drv.write_iso_tracks(t1,t2,t3,dev_ptr)
        if msr605x.track_type == 'raw':
            res = msr605_drv.write_raw_tracks(t1,t2,t3,dev_ptr)
            print(' [-] cannot write in raw mode yet, please: set type iso')
            return True
        if res:
            print(" [+] Written.")
        else:
            print(" [-] Not written")
        return True

    # BULK WRITE
    if cmd_tokens[0] == 'bulk_write':
        print(" [*] Input your data. Enter for not writing to a track.")
        t1 = input(" Track 1: ").strip()
        t2 = input(" Track 2: ").strip()
        t3 = input(" Track 3: ").strip()
        var_msr605_drv = True
        while var_msr605_drv:
            print(" [*] swipe card to write")
            if msr605x.track_type == 'iso':
                res = msr605_drv.write_iso_tracks(t1,t2,t3,dev_ptr)
            if msr605x.track_type == 'raw':
                print(' [-] cannot write in raw mode yet, please: set type iso')
                return True
            if res:
                print(" [+] Written.")
            else:
                print(" [-] Not written")
            next_ = input(" [*] continue? [Yes/no] ")
            if next_.lower() in ("y", "yes"):
                var_msr605_drv = True
            else:
                var_msr605_drv = False
        return True

    # SAVE
    if cmd_tokens[0] == 'save':
        if msr605x.Save != "":
            filename = input(" Filename: ")
            savedata(filename, os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + '/../archives'), msr605x.Save)
            msr605x.Save = ""
        else:
            print(" [*] You should read a card first")
        return True

    # PLAY
    if ((cmd_tokens[0] == 'play') and (len(cmd_tokens) > 3) and (cmd_tokens[2] == 'led')):
        if cmd_tokens[3] == 'on':
            if cmd_tokens[1] == 'all':
                msr605_drv.play_all_led_on(dev_ptr)
            elif cmd_tokens[1] == "g":
                msr605_drv.play_green_led_on(dev_ptr)
            elif cmd_tokens[1] == "y":
                msr605_drv.play_yellow_led_on(dev_ptr)
            elif cmd_tokens[1] == "r":
                msr605_drv.play_red_led_on(dev_ptr)
            else:
                print(' [-] that led color does not exist (g,y,r,all)')
        elif cmd_tokens[3] == 'off':
            msr605_drv.play_all_led_off(dev_ptr)
        else:
            print(' [-] that status does not exist (on,off)')
        return True

    # RESET
    if cmd_tokens[0] == "reset":
        msr605_drv.msr_reset(dev_ptr)
        msr605_drv.set_coercivity("hico",dev_ptr)
        msr605_drv.set_bpc(int(msr605x.bpc[0]), int(msr605x.bpc[1]), int(msr605x.bpc[2]),dev_ptr)
        msr605x.track_type = "iso"
        return True

    # PAN GENERATION
    if cmd_tokens[0] == 'pan':
        if len(cmd_tokens) < 5 and (len(cmd_tokens) < 4 or cmd_tokens[1] != "random"):
            print("Usage:")
            print("  pan random <prefix> <count> <file>")
            print("  pan seq <prefix> <fixed4digits> <file>")
            return True
        if cmd_tokens[1] == "random" and len(cmd_tokens) == 5:
            prefix = cmd_tokens[2]
            count = int(cmd_tokens[3])
            file_path = cmd_tokens[4]
            msr605x.generate_pan_file(file_path, prefix, count=count)
            return True
        elif cmd_tokens[1] == "seq" and len(cmd_tokens) == 5:
            prefix = cmd_tokens[2]
            fixed_digits = cmd_tokens[3]
            file_path = cmd_tokens[4]
            msr605x.generate_pan_file(file_path, prefix, fixed_digits=fixed_digits)
            return True
        else:
            print("Invalid pan command. See 'help' for usage.")
            return True

    # IF COMMAND DOES NOT EXIST
    print(" [*] that command does not exist")
    return False

def main():
    dev = msr_init()
    if not dev:
        print("Device not found")
        return

    print("Firmware version:", get_firmware_version(dev))
    print("Device model:", get_device_model(dev))
    msr_reset(dev)
    set_coercivity('hico', dev)
    set_bpc(0x07, 0x05, 0x05, dev)
    set_bpi("75", "75", "75", dev)

    while True:
        try:
            cmd = input("msr605> ").strip()
            if not cmd:
                continue
            cmd_tokens = cmd.split()
            execute(cmd_tokens, dev)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()

