# Setting up an Azure DSVM for Active Learning

We provide a module that will copy over a shell script to your DSVM and execute the shell script to setup an active learning environment.

We requirement that your ssh key be added to the SSH agent. You can do so my using the **_ssh-add_** command

```sh
$ ssh-add -K ~/.ssh/act-learn-key
```

To copy and execute the shells script use the following command

```sh
$ python setup-tensorflow.py --host admin@127.0.0.1 -k ~/.ssh/act-learn-key -s setup-tensorflow.sh
```

Note that in the host argument **_admin_**@127.0.0.1 section is the DSVM Admin name and admin@**_127.0.0.1_** is the IP address of the DSVM.