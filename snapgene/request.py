import argparse
import json
import sys

import zmq
from pyclasses.config import Config
from pyclasses.multi_client import MutliClient

parser = argparse.ArgumentParser(
    description="Dispatch commands to snapgene-server",
    epilog="This script will take in a command from the command line or file and "
    "send it to one or more of the active snapgene servers in the configuration file. "
    "When the json object is a json array, then each element of the array is sent individually",
)
parser.add_argument(
    "-f", metavar="FILE", help="read the command[s] from the specified FILE"
)
parser.add_argument(
    "-c", metavar="COMMAND", help="directly specify the COMMAND to be dispatched."
)
parser.add_argument(
    "-s",
    metavar="STRATEGY",
    default="any",
    help='specifies the way a command or commands are sent.  Choices are "any", "all" or '
    'the index of the server. If "any" is specified then when dispatching multiple commands '
    'they will be sent in a load balanced manner. If "all" is specified then each command '
    "will be sent to each and every server instance. If a number is specified then the command "
    'or commands will only be sent to that specific server. The default is "any"',
)
parser.add_argument(
    "-t",
    metavar="TIMEOUT",
    type=float,
    default="10.0",
    help="timeout for any one request in seconds.  For multiple commands as long as one command "
    "is finished before TIMEOUT then the dispatcher will continue.  The default is 10 seconds.",
)
parser.add_argument(
    "-v",
    metavar="VERBOSITY",
    type=int,
    default="0",
    help="sets the verbosity for the script.  A value of 0 is silent, 1 is show all responses, 2 "
    "is show all requests and responses.  The default is 0 (silent)",
)

if len(sys.argv) <= 1:
    parser.print_help()
    sys.exit(1)

args = parser.parse_args()

# get verbosity from command line args
verbosity = args.v

# get command from file or directly from command line
strRequest = ""
if args.c is not None:
    strRequest = args.c
elif args.f is not None:
    try:
        f = open(args.f)
        strRequest = f.read()
        f.close()
    except Exception as e:
        print("Error when loading json file.  Reason: {}".format(e))
        sys.exit(1)

# convert commands from a flat string to json object or array
try:
    jsonRequest = json.loads(strRequest)
except Exception as e:
    print("Error when parsing json request.  Reason: {}".format(e))
    sys.exit(1)

# construct command list of json array or object
if type(jsonRequest) is dict:
    commandList = [jsonRequest]
elif type(jsonRequest) is list:
    commandList = jsonRequest
else:
    print("Command line must be a json object or array")
    sys.exit(2)

# load the configuration.  If a specific index is specified just read that
try:
    config = Config()
    if args.s == "any":
        all = False
        server_ports = config.get_server_ports()
    elif args.s == "all":
        all = True
        server_ports = config.get_server_ports()
    else:
        all = False
        index = int(args.s)
        server_ports = dict()
        server_ports[index] = config.lookup_port(index)
except Exception as e:
    print("Unable to load valid configuration")
    print("Reason:", e)
    sys.exit(2)

# send the commands
try:
    client = MutliClient(server_ports, zmq.Context(), verbosity)
    client.doBatch(commandList, all, int(args.t * 1000))
except Exception as e:
    print("Error when dispatching messages")
    print("Reason:", e)
    sys.exit(3)

client.close()
