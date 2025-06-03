#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import colorama
from colorama import Fore, Back
import shlex
import signal
import pyreadline3
import rlcompleter
import readline
import os, sys
import time 
import optparse
import random
import csv
import logging

import msr605_cmd
import msr605_drv

def optionsManager():
    parser = optparse.OptionParser(sys.argv[0]+" --help")
    parser.add_option('-d','--dev',dest="DEV",type="string",help='(ignored for HID devices)')
    parser.add_option('-t','--type',dest="TYPE",type="string",help='<iso,raw>')
    parser.add_option('-m','--mode',dest="MODE",type="string",help='<hico,loco>')
    parser.add_option('-c','--cmd',dest="CMD",type="string",help='<read,write,...>')
    parser.add_option('-p','--pan',dest="PAN",type="string",help='<generate PANs.>')
    (opt, args) = parser.parse_args()
    return opt

global Save, autoSave, bpc, bpi, mode, track_type

options = optionsManager()

Save = ""
autoSave = False
bpc = ['8', '8', '8'] # bits per character for each track
bpi = ['210', '75', '210'] # bits per inch for each track
mode = options.MODE if options.MODE is not None else 'hico'
track_type = options.TYPE if options.TYPE is not None else 'iso'

def luhn_check(pan):
    digits = [int(d) for d in pan]
    checksum = 0
    double = False
    for i in range(len(digits) - 1, -1, -1):
        d = digits[i] * 2 if double else digits[i]
        checksum += d if d < 10 else d - 9
        double = not double
    return checksum % 10 == 0

def generate_custom_pan(prefix="62728494", length=16):
    """Generates a random valid PAN with Luhn check (default 16 digits)."""
    while True:
        # The body should be (length - len(prefix) - 1) digits, +1 for the checksum
        pan_body = prefix + "".join([str(random.randint(0, 9)) for _ in range(length - len(prefix) - 1)])
        checksum_digit = (10 - sum(int(d) if i % 2 == 0 else sum(divmod(int(d) * 2, 10)) for i, d in enumerate(pan_body[::-1])) % 10) % 10
        pan = pan_body + str(checksum_digit)
        if luhn_check(pan) and len(pan) == length:
            return pan

def generate_sequential_pans(prefix, fixed_digits, length=16):
    """Generates all valid PANs based on a fixed prefix and fixed digits (default 16 digits)."""
    pan_list = []
    variable_digits = length - len(prefix) - len(fixed_digits) - 1
    if variable_digits < 0:
        print("Prefix and fixed_digits are too long for the desired PAN length.")
        return []
    for i in range(10 ** variable_digits):
        pan_body = prefix + fixed_digits + str(i).zfill(variable_digits)
        checksum_digit = (10 - sum(sum(divmod(int(d) * 2, 10)) if idx % 2 == 0 else int(d) 
                               for idx, d in enumerate(pan_body[::-1])) % 10) % 10
        pan = pan_body + str(checksum_digit)
        if luhn_check(pan) and len(pan) == length:
            pan_list.append(pan)
    return pan_list

def generate_pan_file(file_path, prefix, fixed_digits=None, count=None, default_yy="00", default_mm="00"):
    """
    Generates PANs either randomly or sequentially and saves them to a file
    in a format compatible with bulk_read saves (track1/track2/track3).
    """
    try:
        if fixed_digits:
            # Assuming generate_sequential_pans is defined in the same file or imported correctly
            pan_list = generate_sequential_pans(prefix, fixed_digits) #
        else: # random PANs
            # Assuming generate_custom_pan is defined in the same file or imported correctly
            pan_list = [generate_custom_pan(prefix) for _ in range(count)] #
        
        with open(file_path, "w") as file: # Open in text mode, not CSV
            for pan_number_str in pan_list:
                # Track 1 data (typically alphanumeric, name, etc.) - kept empty here
                track1_data = f"%?"
                
                # Track 2 data: Start Sentinel (;) + PAN + Field Separator (=) + Expiry (YYMM) + Service Code (SSS) + End Sentinel (?)
                # The PAN generated is usually 16 digits.
                # Example: ;PAN_NUMBER=YYMMSERVICE_CODE?
                track2_data = f";{pan_number_str}={default_yy}{default_mm}?"
                
                # Track 3 data - kept empty here
                track3_data = f"+?"
                
                file.write(f"track1:{track1_data}\n")
                file.write(f"track2:{track2_data}\n")
                file.write(f"track3:{track3_data}\n")
                # You might want a separator line if writing multiple "cards" to one file,
                # but the bulk_read save format doesn't typically have one between distinct reads.
                # If each file represents one card's data, this is fine. If it's a list,
                # this structure repeated is also fine.

        if pan_list:
            print(f"Generated {len(pan_list)} PAN records and saved to {file_path}")
        else:
            print(f"No PANs generated. File '{file_path}' created (may be empty).")
            
    except Exception as e:
        logging.error(f"PAN file generation failed: {e}") #
        # It's often helpful to print the exception to the console for immediate feedback
        print(f"Error during PAN file generation: {e}")

def tokenize(string):
    """to get a well formed command+args"""
    return shlex.split(string)

def shell_loop(init_cmd):
    # auto-completion
    readline.parse_and_bind("tab: complete")
    readline.set_completer(msr605_cmd.completer)
    readline.parse_and_bind('tab: complete')

    dev_ptr = msr605_drv.msr_init()
    if not dev_ptr:
        print(" [-] Please check that the MSR605X device is connected via USB.")
        sys.exit(1)

    # init
    msr605_drv.msr_reset(dev_ptr)
    msr605_drv.set_coercivity(mode, dev_ptr)
    msr605_drv.set_bpc(int(bpc[0]), int(bpc[1]), int(bpc[2]), dev_ptr)

    c = True
    while c:
        if init_cmd is None:
            # display a command prompt
            cmd = input(Back.WHITE+Fore.RED+' msr605x (help/settings)> '+Back.RESET+Fore.CYAN+' ')
        else:
            cmd = init_cmd

        # tokenize the command input
        cmd_tokens = tokenize(cmd)

        # execute the command
        msr605_cmd.execute(cmd_tokens, dev_ptr)

        if init_cmd is not None:
            c = False

def closeProgram(signal, frame):
    sys.exit(1)

def main():
    signal.signal(signal.SIGINT, closeProgram) # close program with Ctrl+C
    if options.PAN is not None:
        # Usage: --pan random:<prefix>:<count> or --pan seq:<prefix>:<fixed4digits>
        pan_args = options.PAN.split(':')
        if pan_args[0] == 'random' and len(pan_args) == 3:
            prefix = pan_args[1]
            count = int(pan_args[2])
            file_path = f"random_pans_{prefix}_{count}.txt"
            generate_pan_file(file_path, prefix, count=count)
        elif pan_args[0] == 'seq' and len(pan_args) == 3:
            prefix = pan_args[1]
            fixed_digits = pan_args[2]
            file_path = f"seq_pans_{prefix}_{fixed_digits}.txt"
            generate_pan_file(file_path, prefix, fixed_digits=fixed_digits)
        else:
            print("Invalid --pan argument. Use random:<prefix>:<count> or seq:<prefix>:<fixed4digits>")
        return
    if options.CMD is not None:
        init_cmd = options.CMD
    else:
        init_cmd = None
    shell_loop(init_cmd)

if __name__ == '__main__':
    main()

