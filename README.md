ev3dev_examples
===============

Examples of program for ev3dev

Installation
===============
For python/rubiks_test.py:
- apt-get install python-pip python-dev python-numpy
- pip install colormath


UI
==
- Hold down the center button for several seconds to exit the program (the LED
  will turn yellow). This is handy if the arm fails to flip the cube and you
  want to stop and start over.
- If you have a server.conf file but cannot reach the server the LED will change
  to orange. The color analyzer and solution program will both run on the ev3
  so orange is a sign that things will run a little slower.
- If we hit an eror the LED will turn RED. Check the rubiks.log file to see what
  went wrong.

Server
======
It is possible to run the color analyzing software and the rubiks cube solution
software on the ev3 but there are two advantages in offloading this to a much
faster server:

- When run on a server, the color analyzer will use a more CPU intensive algorithm
  and will return more reliable results.
- When run on a server, utils/rubiks_solvers/twophase_python/solve.py is used to
  calculate the solution.  This normally returns a solution that takes about 20 steps.
  This is compared to a solution in the 60 to 100 steps range if you use cubex on the ev3.

To use a server create an ev3dev_examples/python/server.conf file that has the following fields

dwalton76@ev3dev[python]# cat server.conf
username=dwalton76
ip=192.168.0.13
path=/home/dwalton76/ev3dev_examples/
dwalton76@ev3dev[python]#

You will need to create ssh keys so that you can login without a password
http://www.thegeekstuff.com/2008/11/3-steps-to-perform-ssh-login-without-password-using-ssh-keygen-ssh-copy-id/
