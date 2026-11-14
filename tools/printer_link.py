"""Talk to an Elegoo Neptune 4 over its front USB-C port (macOS, Windows, Linux).

The USB-C port is a serial console on the printer's built-in Linux computer.
Someone must already be logged in on it (log in once with a terminal program,
then close that program), because this tool never types passwords.

Usage:
  python tools/printer_link.py ports                 list serial ports
  python tools/printer_link.py run "COMMAND"         run a shell command on the printer
  python tools/printer_link.py send drawing.gcode    copy a drawing into ~/gcode_files
  python tools/printer_link.py install               install ~/pen/*.sh and pen mode

Add --port PORT to choose the port yourself (e.g. --port COM5 or
--port /dev/cu.usbserial-1410); otherwise the printer's USB chip is found
automatically.
"""
import argparse
import base64
import gzip
import hashlib
import pathlib
import random
import sys
import time

import serial
import serial.tools.list_ports

BAUD = 1500000
CH340_VID = 0x1A86  # the USB-serial chip on the Neptune 4's front port
REPO = pathlib.Path(__file__).resolve().parent.parent


def find_port():
    ports = [p for p in serial.tools.list_ports.comports() if p.vid == CH340_VID]
    if not ports:
        sys.exit("Printer not found. Is the USB-C cable plugged in and the printer on? "
                 "(Run 'ports' to list what is connected, then use --port.)")
    # On macOS each port appears as tty.* and cu.*; cu.* is the right one to open.
    ports.sort(key=lambda p: "/cu." not in p.device)
    return ports[0].device


class Printer:
    def __init__(self, port):
        try:
            self.ser = serial.Serial(port, BAUD, timeout=0.1)
        except serial.SerialException as e:
            sys.exit("Can't open %s (%s). Close PuTTY/screen/CoolTerm and try again." % (port, e))

    def close(self):
        self.ser.close()

    def _read_until(self, marker, timeout):
        buf, end = "", time.time() + timeout
        while time.time() < end:
            buf += self.ser.read(4096).decode("utf-8", "replace")
            if marker in buf:
                return buf
        return None

    def run(self, cmd, timeout=15):
        """Run a shell command and return what it printed."""
        marker = "__END_%d__" % random.randrange(10 ** 9)
        self.ser.reset_input_buffer()
        # stty -echo keeps the typed command out of the output.
        self.ser.write(("stty -echo; %s; echo %s\n" % (cmd, marker)).encode())
        out = self._read_until("\n" + marker, timeout)
        self.ser.write(b"stty echo\n")
        if out is None:
            sys.exit("No answer from the printer. Is someone logged in on its console? "
                     "Log in once (user mks) with a terminal program, then close it.")
        lines = out.split("\n" + marker)[0].splitlines()
        return "\n".join(lines[1:] if lines and "stty -echo" in lines[0] else lines)

    def upload(self, src, dest):
        """Copy a local file to `dest` on the printer and check it arrived intact."""
        data = pathlib.Path(src).read_bytes()
        md5 = hashlib.md5(data).hexdigest()
        b64 = base64.b64encode(gzip.compress(data)).decode()
        lines = [b64[i:i + 76] for i in range(0, len(b64), 76)]

        self.ser.write(b"stty -echo\n")
        time.sleep(0.3)
        self.ser.write(("base64 -d << 'B64EOF' | gunzip > '%s.tmp'\n" % dest).encode())
        time.sleep(0.2)
        # Small chunks with pauses so the printer's input buffer never overflows.
        for i in range(0, len(lines), 20):
            self.ser.write(("\n".join(lines[i:i + 20]) + "\n").encode())
            time.sleep(0.04)
            self.ser.read(4096)
        self.ser.write(b"B64EOF\n")
        time.sleep(0.8)
        self.ser.reset_input_buffer()
        check = ("if [ \"$(md5sum < '{d}.tmp' | cut -d' ' -f1)\" = '{m}' ]; then mv '{d}.tmp' '{d}'; "
                 "echo UPLOAD_OK; else rm -f '{d}.tmp'; echo UPLOAD_BAD; fi; stty echo\n")
        self.ser.write(check.format(d=dest, m=md5).encode())
        out = self._read_until("UPLOAD_", 15) or ""
        time.sleep(0.2)
        out += self.ser.read(4096).decode("utf-8", "replace")
        if "UPLOAD_OK" not in out:
            sys.exit("Upload of %s failed or could not be checked. Try again." % src)
        print("Sent %s -> %s (%d bytes, checked)" % (pathlib.Path(src).name, dest, len(data)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port")
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("ports")
    run = sub.add_parser("run")
    run.add_argument("command")
    send = sub.add_parser("send")
    send.add_argument("file")
    sub.add_parser("install")
    a = ap.parse_args()

    if a.action == "ports":
        for p in serial.tools.list_ports.comports():
            tag = "  <- printer" if p.vid == CH340_VID else ""
            print("%-30s %s%s" % (p.device, p.description, tag))
        return

    printer = Printer(a.port or find_port())
    try:
        if a.action == "run":
            print(printer.run(a.command, timeout=60))
        elif a.action == "send":
            name = pathlib.Path(a.file).name
            printer.upload(a.file, "/home/mks/gcode_files/" + name)
        elif a.action == "install":
            printer.run("mkdir -p ~/pen")
            for f in sorted((REPO / "printer_scripts").glob("*.sh")):
                printer.upload(f, "/home/mks/pen/" + f.name)
            printer.upload(REPO / "printer_config" / "pen_plotter.cfg",
                           "/home/mks/klipper_config/pen_plotter.cfg")
            # Strip any Windows line endings and make the scripts runnable.
            printer.run(r"sed -i 's/\r$//' ~/pen/*.sh ~/klipper_config/pen_plotter.cfg; chmod +x ~/pen/*.sh")
            print(printer.run("~/pen/pen_mode_on.sh", timeout=30))
            print("Installed. Commands on the printer: " + printer.run("ls ~/pen | tr '\\n' ' '"))
    finally:
        printer.close()


if __name__ == "__main__":
    main()
