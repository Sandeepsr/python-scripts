#!/usr/bin/env python
""" Author : ip.sandeep@live.com
        Date: 9/22/2016
        Tested on Python 2.7
        Sample Usage:
        $ python show_command_threaded.py --cmdfile cmd_file.txt --devicefile device_file.txt"""


#Import modules
import re
import os
import paramiko
import time
import sys
import getpass
import argparse
import threading
from time import strftime
from Queue import Queue
from datetime import datetime
import logging


__script_name__ = os.path.basename(sys.argv[0])


MAX_BUFFER = 65535


# Parse command line args some different steps
parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
parser.add_argument('--cmdfile', required=True, help="File name containing a newline delimited list of commands to run against")
parser.add_argument('--devicefile', required=True, help="File name containing a newline delimited list of devices to run against")
args = parser.parse_args()



username = raw_input('Please enter your username:  ')
print ('Your username is {0} ').format(username)
password = getpass.getpass()
cmd_file = args.cmdfile
device_file = args.devicefile

def CheckCmdFile(cmd_file):
    Inputlist =[]
    #Changing exception message
    try:
        #Open user selected file for reading (File containing PDU names separated by newline.)
        with open(cmd_file, 'r') as h:
            logging.info("Opening file...<cmdfile.txt>")
            lines = h.readlines()
            for line in lines:
                command = line.rstrip('\n').strip('\t').strip()
                if not (command.lower().startswith('sh') or command.lower().startswith('show')):
                    print ('\nERROR: Unexpected show command <{}> try again!').format(command)
                    logging.error('Unexpected command not starting with sh* . Try again!')
                    sys.exit()
                else:
                    Inputlist.append(command)
                    if not Inputlist:
                        print '\nERROR: cmd_file.txt is empty..try again! '
                        sys.exit()
        print '\nINFO: cmd_file is okay !!!\n'
        return Inputlist
    except IOError:
        print "\n File cmd_file does not exist! Please check and try again!\n"
        logging.error('File cmd_file does not exist! Please check and try again!')
        sys.exit()
    except Exception as e:
        print "\nError: {}".format(e)
        logging.error('Error: {}'.format(e))




def CheckDeviceFile(device_file):
    Inputlist =[]
    #Changing exception message
    try:
        #Open user selected file for reading (File containing PDU names separated by newline.)
        with open(device_file, 'r') as h:
            logging.info("Opening file...<device_file.txt>")
            lines = h.readlines()
            if not lines:
                print "device_file.txt is empty"
                sys.exit()
            for line in lines:
                device = line.rstrip('\n').strip('\t').strip()
                Inputlist.append(device)
                if not Inputlist:
                    print '\nERROR: device_file.txt is empty..try again! '
                    sys.exit()
        print '\nINFO: device_file.txt is okay !!!\n'
        return Inputlist
    except IOError:
        print "\n File device_file.txt does not exist! Please check and try again!\n"
        logging.error('File device_file.txt does not exist! Please check and try again!')
        sys.exit()
    except Exception as e:
        print "\nError: {}".format(e)
        logging.error('Error: {}'.format(e))



def Create_Filename(name, file_type):
    temp_name = ''

    temp = strftime('%X').split(':')
    temp1 = strftime('%x').split('/')
    for x in range(0, len(temp1)):
        temp_name += temp1[x]

    temp_name += '_'

    for x in range(0, len(temp)):
        temp_name += temp[x]

    return name + "_" + temp_name + "." + file_type


def GetDeviceConfig(ip,command,delay_factor=2,max_loops=30):
    output = str()
    try:
        session = paramiko.SSHClient()
        session.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        session.connect(ip, username = username, password = password)
        connection = session.invoke_shell()
        connection.send("term len 0\n")
        connection.send(command)
        for i in xrange(max_loops):
            time.sleep(2 * delay_factor)
            if connection.recv_ready():
                output += connection.recv(MAX_BUFFER)
                # Check for Invalid command
                if 'invalid' in output.lower():
                    message = "Invalid Command sent: {}, error message: {}".format(command, output)
                    print 'Invalid comamnd found...', message
            else:
                print "recv_ready = False "
                print "\nDONE for device %s" % ip
                session.close()
                return output
    except paramiko.AuthenticationException:
        print "* Invalid username or password. \n* Please check the username/password file or the device configuration!", ip
        pass
    except Exception as e:
        print 'Error in connection {} , Device : {}'.format(e , ip)
        pass


#Open SSHv2 connection to devices
def open_ssh_conn(results,q):
    while not q.empty():
        work = q.get()
        #print 'Working in device...',work[1].hostname
        try:
            #Open user selected file for reading
            selected_cmd_file = open(cmd_file, 'r')
            #Starting from the beginning of the file
            selected_cmd_file.seek(0)
            #Writing each line in the file to the device
            out_all = str()
            for each_line in selected_cmd_file.readlines():
                output = GetDeviceConfig(work[1],each_line)
                out_all += work[1] +'#' + each_line + '\n'
                out_all += output + '\n'
            results[work[0]] = out_all
            #Closing the command file
            selected_cmd_file.close()
            if re.search(r"% Invalid input detected at", output):
                print "* There was at least one IOS syntax error on device %s" % work[1]
            else:
                print "DONE for device %s" % work[1]
            q.task_done()
        except Exception as e:
            print "Error: ", e
            q.task_done()
        return True


def get_all_queue_result(queue):

    result_list = []
    while not queue.empty():
        result_list.append(queue.get())

    return result_list

threads = []
#Creating threads
def create_threads():
        try:
            for ii in range(num_threads):
                #print 'starting thread....'
                logging.debug("Creating threads number :{}".format(ii))
                th = threading.Thread(target = open_ssh_conn, args = (results, q))   #args is a tuple with a single element
                th.setDaemon(True)
                th.start()
                threads.append(th)
            return True
        except Exception as e:
            print "\nError: {}".format(e)



#Variables and main program
commandlist = CheckCmdFile(cmd_file)
devicelist = CheckDeviceFile(device_file)


print "\nTotal Devices : ", len(devicelist)

for device in devicelist:
    print device

go_ahead = raw_input('Please enter any key to continue or Ctrl C/Z to quit ')
print ('Connecting to devices...')

#set up the queue to hold all the devices...
q = Queue(maxsize=0)
#Use many threads (20 max, or one for each device)...
print '\nINFO: Maximum 20 threads will be running in parallel..\n'
num_threads = min(20, len(devicelist))


results = [{} for device in devicelist];
#load up the queue with the device to fetch and the index for each job (as a tuple):
for i in range(len(devicelist)):
    #need the index and the device in each queue item.
    q.put((i,devicelist[i]))

#print 'Calling threads creation function....'
total_items = len(devicelist)
# Record start time
start_time = datetime.now()

while total_items >=0:
    create_threads()
    total_items -= num_threads
    #print total_items


logging.info('Starting to join threads...Please wait for a moment')

#join threads
for t in threads:
    q.join()

logging.info('Done with all items in queue ...')
print

output_filename = Create_Filename('output', 'txt')


for item in results:
    f_o = open(output_filename, 'a')
    print >> f_o, '*************************************************'
    #print '*************************************************'
    print >> f_o, "\n"
    #print "\n"
    print>>f_o, item
    #print 'Device : ', item
    f_o.close()

logging.info('All tasks completed.')
end_time = datetime.now()
print
print "-------------------------- RESULTS ------------------------------------------"
print "-----------------------------------------------------------------------------"
print "Total Devices :", len(devicelist)
print "File {0} has been created".format(output_filename)
print "This script ran for :", end_time - start_time
print "----------------------------------------------------------------------------\n"
