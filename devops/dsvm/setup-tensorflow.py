import os
import argparse
from fabric import *

def get_connection(dsvm_host,ssh_key_path):
    #http://docs.fabfile.org/en/2.4/api/connection.html
    return Connection(host=dsvm_host,connect_kwargs={"key_filename": ssh_key_path})

def main(host,ssh_key_path,script_path):
    #ip_address = 'abrig@13.68.227.63'
    #local_ssh_key_path = '/Users/andrebriggs/.ssh/act-learn-key'
    #tf_setup_script = "setup-tensorflow.sh"

    no_errors = True
    try:      
        with get_connection(host,ssh_key_path) as c:
            result = c.run("rm -f ~/{0}".format(script_path))
            print("Ran {0.command!r} on {0.connection.host}, got stdout:\n{0.stdout}".format(result))
            print("Copying {0} to remote machine at {1}".format(script_path,host))
            c.put(script_path)
            print("Executing {0} on  remote machine".format(script_path))
            result = c.run("sh {0}".format(script_path))
    except Exception as e:
            print(str(e))
            no_errors = False
    finally:
        return no_errors

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sets up an active learning environment on a DSVM")

    parser.add_argument('--host', default=os.environ.get('DSVM_HOST', None), 
        help="A host name in the form of (UserName)@IpAddress (e.g. admin@127.0.0.1)")

    parser.add_argument('-k','--sshKeyPath', default=os.environ.get('DSVM_SSH_KEY_PATH', None),
        help="Path to local private key for VM. (e.g. /Users/JohnDoe/.ssh/act-learn-key). Be sure run ssh-add -K ~/.ssh/act-learn-key first")

    parser.add_argument('-s','--scriptPath', default=os.environ.get('DSVM_SCRIPT', None),
        help="Path to script that will be copied to DSVM and executed")

    args = parser.parse_args()

    if not args.host or not args.sshKeyPath or not args.scriptPath:
        exit(parser.print_usage())

    main(args.host,args.sshKeyPath,args.scriptPath)           

