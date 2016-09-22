# python-scripts

This is a multithreaded script to intract with cisco/arista network ddevices. Can be used to get output from multiple device of same vendor pretty quickly.

Make sure you have cmd_file.txt  and device_file.txt  named text files containing commands and device IP/devicename respectively , separated by a new line.

Example ussge:
$ python cmd_outV2.py --cmdfile cmd_file.txt --devicefile device_file.txt
