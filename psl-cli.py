#!/usr/bin/python
# -*- coding: utf-8 -*-
"Main Program executed by the user"

import argparse
import sys
from psl_class import ProSafeLinux
import psl_typ

# pylint: disable=W0613


def discover(args, switch):
    "Search for Switches"
    print("Searching for ProSafe Plus Switches ...\n")
    found = False
    for data in switch.discover():
        found = True
        for entry in data.keys():
            print(entry.get_name() + ': ' + data[entry])
        print("")

    if not found:
        print("No result received...")
        print("did you try to adjust your timeout?")

# pylint: enable=W0613

def exploit(args, switch):
    "exploit in current (2012) fw, can set a new password"
    switch.passwd_exploit(args.mac[0], args.new_password[0])
    
def set_switch(args, switch):
    "Set values on switch"
    cmds = {ProSafeLinux.CMD_PASSWORD: args.passwd[0]}
    for scmd in switch.get_setable_cmds():
        if vars(args)[scmd.get_name()] is not None:
            if isinstance(scmd, psl_typ.PslTypAction):
                if vars(args)[scmd.get_name()]:
                    cmds[scmd] = True
            else:
                if isinstance(scmd, psl_typ.PslTypBoolean):
                    cmds[scmd] = (vars(args)[scmd.get_name()][0] == "on")
                else:
                    if len(vars(args)[scmd.get_name()])==1:
                        cmds[scmd] = vars(args)[scmd.get_name()][0]
                    else:
                        cmds[scmd] = vars(args)[scmd.get_name()]

    valid, errors = switch.verify_data(cmds)
    if not valid:
        for error in errors:
            print(error)
    else:
        print("Changing Values..\n")
        result = switch.transmit(cmds, args.mac[0])
        if 'error' in result:
            print("FAILED: Error with " + str(result['error']))


def query(args, switch, querycommand = None):
    "query values from the switch"
    if not(args.passwd == None):
        login = {switch.CMD_PASSWORD: args.passwd[0]}
        switch.transmit(login, args.mac[0])
    query_cmd = []
    if querycommand != None:
        query_cmd.append(querycommand)
    else:
        print("Query Values..\n")
        for qarg in args.query:
            if qarg == "all":
                for k in switch.get_query_cmds():
                    query(args, switch, querycommand=k)
                return
            else:
                query_cmd.append(switch.get_cmd_by_name(qarg))
    switchdata = switch.query(query_cmd, args.mac[0])
    if switchdata != False:
        if switchdata == {}:
            print("%-29s empty data received" % (query_cmd[0].get_name()))
        else:
            for key in list(switchdata.keys()):
                if isinstance(key, psl_typ.PslTyp):
                    key.print_result(switchdata[key])
                else:
                    if args.debug:
                        print("-%-29s%s" % (key, switchdata[key]))
    else:
        print("-- %s --" % (query_cmd[0].get_name()))
        print("No result received...")
        print("did you try to adjust your timeout?")
    print("")


def query_raw(args, switch):
    "get all values, even unknown"
    print("QUERY DEBUG RAW")
    if not(args.passwd == None):
        login = {switch.CMD_PASSWORD: args.passwd[0]}
        switch.transmit(login, args.mac[0])
    i = 0x0001
    while (i < ProSafeLinux.CMD_END.get_id()):
        query_cmd = []
        query_cmd.append(psl_typ.PslTypHex(i, "Command %d" % i))
        try:
            switchdata = switch.query(query_cmd, args.mac[0])
            found = None
            for qcmd in list(switchdata.keys()):
                if (isinstance(qcmd, psl_typ.PslTyp)):
                    if qcmd.get_id() == i:
                        found = qcmd

            if found is None:
                print("NON:%04x:%-29s:%s" % (i, "", switchdata["raw"]))
            else:
                print("RES:%04x:%-29s:%s " % (i, switchdata[found],
                    switchdata["raw"]))
            if args.debug:
                for key in list(switchdata.keys()):
                    print("%x-%-29s%s" % (i, key, switchdata[key]))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            print("ERR:%04x:%s" % (i, sys.exc_info()[1]))
        i = i + 1


def main():
    "main program"
    cmd_funcs = {
        "discover": discover,
        "set": set_switch,
        "query": query,
        "query_raw": query_raw,
        "exploit": exploit,
    }

    switch = ProSafeLinux()
    parser = argparse.ArgumentParser(
        description='Manage Netgear ProSafe Plus switches under Linux.')
    parser.add_argument("--interface", nargs=1, help="Interface",
        default=["eth0"])
    parser.add_argument("--debug", help="Debug output", action='store_true')
    parser.add_argument("--timeout", help="set timeout for switch commands",
                default="0.1", type=float)
    subparsers = parser.add_subparsers(help='operation', dest="operation")

    subparsers.add_parser('discover', help='Find all switches in all subnets')
    
    exploit_parser = subparsers.add_parser("exploit",
       help="set a password without knowing the old one")
    exploit_parser.add_argument("--mac", nargs=1,
        help="Hardware address of the switch", required=True)
    exploit_parser.add_argument("--new_password", nargs=1,
        help="password",required=True)

    query_parser = subparsers.add_parser("query",
        help="Query values from the switch")
    query_parser.add_argument("--mac", nargs=1,
        help="Hardware address of the switch", required=True)
    query_parser.add_argument("--passwd", nargs=1, help="password")
    choices = []
    for cmd in switch.get_query_cmds():
        choices.append(cmd.get_name())
    choices.append("all")
    
    query_parser.add_argument("query", nargs="+", help="What to query for",
        choices=choices)

    query_parser_raw = subparsers.add_parser("query_raw",
        help="Query raw values from the switch")
    query_parser_raw.add_argument("--mac", nargs=1,
        help="Hardware address of the switch", required=True)
    query_parser_raw.add_argument("--passwd", nargs=1,
        help="password")

    set_parser = subparsers.add_parser("set", help="Set values to the switch")
    set_parser.add_argument("--mac", nargs=1,
        help="Hardware address of the switch", required=True)
    set_parser.add_argument("--passwd", nargs=1, help="password", required=True)

    for cmd in switch.get_setable_cmds():
        if isinstance(cmd, psl_typ.PslTypAction):
            set_parser.add_argument("--" + cmd.get_name(),
                dest=cmd.get_name(), action='store_true')

        else:
            set_parser.add_argument("--" + cmd.get_name(), 
                nargs=cmd.get_num_args(),
                type=cmd.get_set_type(),
                help=cmd.get_set_help(),
                metavar=cmd.get_metavar(),
                choices=cmd.get_choices())

    args = parser.parse_args()
    interface = args.interface[0]

    switch.set_timeout(args.timeout)

    if not switch.bind(interface):
        print("Interface has no addresses, cannot talk to switch")
        return

    if (args.debug):
        switch.set_debug_output()

    if args.operation in cmd_funcs:
        cmd_funcs[args.operation](args, switch)
    else:
        print("ERROR: operation not found!")

main()

# vim:filetype=python:foldmethod=marker:autoindent:expandtab:tabstop=4
