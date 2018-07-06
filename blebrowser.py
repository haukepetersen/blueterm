#!/usr/bin/env python3

import cmd
import argparse
from enum import Enum
from bluepy.btle import Scanner, Peripheral, ADDR_TYPE_PUBLIC, UUID, DefaultDelegate

# global configuration
cfg = dict()
cfg['intro'] = "Welcome to blueterm - Type 'help' or '?'' to list commands.\n"
cfg['prompt'] = "~ "


# class ScanDelegate(DefaultDelegate):
#     def __init__(self):
#         DefaultDelegate.__init__(self)

#     def handleDiscovery(self, dev, isNewDev, isNewData):
#         if isNewDev:
#             print("Discovered device", dev.addr)
#         elif isNewData:
#             print("Received new data from", dev.addr)

# scanner = Scanner().withDelegate(ScanDelegate())
# devices = scanner.scan(2.0)

# print("num of", len(devices))

# for dev in devices:
#     print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
#     print(dev.getScanData())
#     for (adtype, desc, value) in dev.getScanData():
#         print("  %s = %s" % (desc, value))

class ShellEventHandler(DefaultDelegate):

    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, handle, data):
        print("Got notification: {}, {}".format(handle, data))

    def handleDiscovery(scanEntry, isNewDev, isNewData):
        print("new discovery: {}, {}".format(isNewDev, isNewData))


class Blueterm(cmd.Cmd):
    intro = cfg['intro']
    prompt = cfg['prompt']

    class State(Enum):
        IDLE = 1
        CONNECTED = 2


    def __init__(self, device_index, scan_timeout):
        cmd.Cmd.__init__(self)
        self.device_index = device_index
        self.scan_timeout = scan_timeout
        self.ble_devs = set()
        self.ble_gatt = dict()
        self.chars = dict()
        self.state = self.State.IDLE

        # setup Bluetooth
        self.scanner = Scanner(device_index)
        self.periph = Peripheral(None, ADDR_TYPE_PUBLIC, device_index)
        self.periph.setDelegate(ShellEventHandler())

    # Pla
    def precmd(self, line):
        return line

    def do_state(self, line):
        """Print current connection state
        """
        if self.state == self.State.CONNECTED:
            print("Connected to {}".format(self.periph.addr))
        else:
            print(self.state)

    def do_scan(self, line):
        """Scan for available BLE RIOT shells.
Running this command will reset the cached list of available devices.
usage: scan <scan timeout in sec>
        """
        args = line.strip().split(' ')
        if len(args[0]) > 0:
            try:
                to = float(args[0])
            except:
                print("error: unable to parse timeout (must be a number)")
                return
        else:
            to = self.scan_timeout

        print("Scanning now (blocking for {} seconds)...".format(to))
        try:
            self.ble_devs = list(self.scanner.scan(to))
            print("Scan complete:")
            self.do_list("")
        except:
            print("error: failure while scanning")
            return

    def do_list(self, line):
        """List all available BLE devices offering a RIOT shell
        """
        if len(self.ble_devs) == 0:
            print("No BLE devices available")
            return

        for i, dev in enumerate(self.ble_devs):
            print("[{:2}] {}".format(i, dev.addr), end='')
            for (adtype, desc, value) in dev.getScanData():
                if adtype == 9:
                    print(" (Name: '{}'')".format(value), end='')
            print()

    def do_connect(self, line):
        args = line.strip().split(' ')
        if len(args[0]) == 0:
            print("usage: connect <device index>")
            return
        try:
            dev = self.ble_devs[int(args[0])]
        except:
            print("error: unable to find given device index")
            return

        try:
            self.periph.connect(dev.addr, dev.addrType)
            services = self.periph.getServices()
            for i, service in enumerate(services):
                print("     Service {:2} UUID: {} ({})".format(i, service.uuid,
                      service.uuid.getCommonName()))
                chars = service.getCharacteristics()
                type(chars)
                for i, char in enumerate(chars):
                    self.chars[char.getHandle()] = char
                    print("{:5}   Char {:2} UUID: {} ({})".format(char.getHandle(), i, char.uuid,
                          char.uuid.getCommonName()))
                    # if char.supportsRead():
                    #     tmp = char.read()
                    #     print("Data: ", str(tmp))
            self.state = self.State.CONNECTED
        except:
            print("error: while conneting something was bad")
            return


    def do_disconnect(self, line):
        """Close any open connection
        """
        self.periph.disconnect()
        self.chars = dict()
        self.state = self.State.IDLE
        print(self.periph.addr)


    def do_read(self, line):
        try:
            handle = int(line.strip())
            char = self.chars[handle]
            if not char.supportsRead():
                print("error: characteristic is not readable")
            else:
                buf = char.read()
                print("out: {}".format(buf.decode('utf-8')))
        except:
            print("usage: read <handle>")
            return


    def do_write(self, line):
        cmd = line.strip().partition(' ')
        if not cmd[2]:
            print("usage: write <handle> <data>")
            return

        try:
            handle = int(cmd[0])
            char = self.chars[handle]
            char.write(cmd[2].encode('utf-8'))
        except:
            print("error: unable to find characteristic")




if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Blueterm - Access the RIOT "
                                            "shell over BLE")
    p.add_argument("-d", "--device_index", type=int,
                   help="Bluetooth device, default: 0:=/dev/hci0", default=0)
    p.add_argument("-s", "--scan_timeout", type=float,
                   help="Number seconds to scan for BLE devices", default=3.0)
    args = p.parse_args()

    prompt = Blueterm(args.device_index, args.scan_timeout)
    prompt.cmdloop()
