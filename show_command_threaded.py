""" Author : ip.sandeep@live.com
	Date: 5/2/2016
	
	Sample Usage: 
	$ python show_cmd_threaded.py --cmdfile cmd_file.txt --devicefile device_file.txt 
"""


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

	
#Open SSHv2 connection to devices
def open_ssh_conn(results,q):
    #print 'First thread....'
    while not q.empty():
        work = q.get()
	#print 'Working in device...',work[1]
	try:
	    #defining the user and credential file
	    #Logging into device
	    session = paramiko.SSHClient()
	    session.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	    session.connect(work[1], username = username, password = password)
	    connection = session.invoke_shell()	
	    #Setting terminal length for entire output - no pagination
	    connection.send("term len 0\n")
	    time.sleep(1)
	    for item in commandlist:
		connection.send(item + '\n')
		time.sleep(2)
		connection.send("\n")
		time.sleep(1)
		connection.send("\n")
		time.sleep(2)
	    #Checking command output for IOS syntax errors
	    output = connection.recv(65535)
	    results[work[0]] = output
	    if re.search(r"% Invalid input detected at", output):
		print "* There was at least one IOS syntax error on device %s" % work[1]
	    else:
		print "DONE for device %s" % work[1]
	    #Closing the connection
	    session.close()
	    q.task_done()   
	except paramiko.AuthenticationException:
	    print "* Invalid username or password. \n* Please check the username/password file or the device configuration!"
	    print "* Closing program...\n"
	return True


def get_all_queue_result(queue):

    result_list = []
    while not queue.empty():
        result_list.append(queue.get())

    return result_list


#Creating threads
def create_threads():
	try:
	    for ii in range(num_threads):
		#print 'starting thread....'
		logging.debug("Creating threads number :{}".format(ii))
		th = threading.Thread(target = open_ssh_conn, args = (results, q))   #args is a tuple with a single element
		th.setDaemon(True)
		th.start()
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
	
logging.info('Done with all items in queue ...')
print
logging.info('Starting to join threads...Please wait for a moment')

#join threads		
q.join()

output_filename = Create_Filename('show_cmd_output', 'txt')
f_o = open(output_filename, 'a')

for item in results:
    print >> f_o, '*************************************************'
    #print '*************************************************'
    print >> f_o, "\n"
    #print "\n"    
    print>>f_o, item
    #print 'Device : ', item

logging.info('All tasks completed.')
end_time = datetime.now()
print
print "-------------------------- RESULTS ------------------------------------------"
print "-----------------------------------------------------------------------------"
print "Total Devices :", len(devicelist)
print "File {0} has been created".format(output_filename)
print "This script ran for :", end_time - start_time
print "----------------------------------------------------------------------------\n"
