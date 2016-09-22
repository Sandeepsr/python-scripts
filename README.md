# python-scripts

This is a multithreaded script to intract with cisco/arista network devices. Can be used to get output from multiple device of same vendor pretty quickly.

It uses paramiko to ssh to devices.

Make sure you have "cmd_file.txt"  and "device_file.txt"  named text files containing commands and device IP/devicename respectively , separated by a new line. Should be in same directoty as script.

Example ussge:
$ show_command_threaded.py --cmdfile cmd_file.txt --devicefile device_file.txt
