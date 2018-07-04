#!/usr/bin/env python3

import cmd
import argparse
from bluepy.btle import Scanner, Peripheral, ADDR_TYPE_PUBLIC, UUID, DefaultDelegate

# global configuration
cfg = dict()
cfg['intro'] = "Welcome to blueterm - Type 'help' or '?'' to list commands.\n"
cfg['prompt'] = "(blueterm) "
cfg['uuid_riot_shell'] = UUID("00002a00-0000-1000-8000-00805f9b34fb")

# global state


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

    def __init__(self, device_index, scan_timeout):
        cmd.Cmd.__init__(self)
        self.device_index = device_index
        self.scan_timeout = scan_timeout
        self.ble_devs = set()
        self.ble_gatt = dict()

        # setup Bluetooth
        self.scanner = Scanner(device_index)
        self.periph = Peripheral(None, ADDR_TYPE_PUBLIC, device_index)
        self.periph.setDelegate(ShellEventHandler())

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
        self.ble_devs = list(self.scanner.scan(to))
        print("Scan complete:")
        self.do_list("")

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

        self.periph.connect(dev.addr, dev.addrType)
        services = self.periph.getServices()
        for i, service in enumerate(services):
            print("Service {:2} UUID: {} ({})".format(i, service.uuid,
                  service.uuid.getCommonName()))
            chars = service.getCharacteristics()
            type(chars)
            for i, char in enumerate(chars):
                print("Char {:2} UUID: {} ({})".format(i, char.uuid,
                      char.uuid.getCommonName()))
                try:
                    char.write(b'\1')
                except:
                    print("unable to write char {}".format(char.uuid))
                if char.uuid == cfg['uuid_riot_shell']:
                    tmp = char.read()
                    print("Data: ", str(tmp))



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
