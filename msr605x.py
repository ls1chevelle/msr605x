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

import msr605_cmd
import msr605_drv

def optionsManager():
    parser = optparse.OptionParser(sys.argv[0]+" --help")
    parser.add_option('-d','--dev',dest="DEV",type="string",help='(ignored for HID devices)')
    parser.add_option('-t','--type',dest="TYPE",type="string",help='<iso,raw>')
    parser.add_option('-m','--mode',dest="MODE",type="string",help='<hico,loco>')
    parser.add_option('-c','--cmd',dest="CMD",type="string",help='<read,write,...>')
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
    if options.CMD is not None:
        init_cmd = options.CMD
    else:
        init_cmd = None
    shell_loop(init_cmd)

if __name__ == '__main__':
    main()

