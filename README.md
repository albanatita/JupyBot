# JupyBot
## we can say it is a very early zeta version

Welcome on the README page of the JupyBot.
This is a **proof of concept **for a bot suited for the [matrix.org](https://matrix.org/) federation of servers. It can be used with whatever client (for instance [riot.im](https://riot.im)') available for the network.

The purpose of the bot is to provide a link with [Jupyter](https://jupyter.org/) kernels running either on your local computer or somewhere else on a server. 
You can access your kernels through the bot with the chat interface. The kernels will answer to your commands through the same interface.

### Requirements with the present version
It corresponds to the version I have tested. It may work in rather different conditions as well provided minor modifications
- Tested on Debian 10
- Python 3
- [nio-matrix](https://github.com/kiliankoe/nio) client library, to be installed with _pip3_
- Docker
- Jupyter stack with [Jupyter Kernel Gateway](https://github.com/jupyter/kernel_gateway). The stack is provided in a docker container.

### Start up
There are some steps involved, not everything is not yet automated. The focus now is on the bot working and checking what users need.
We start the Jupyter kernel gateway and the associated Jupyter server:
- clone the present repository from github
- go into the _gateway_ directory
- launch `start.sh`
This is it for the Jupyter part. Of course, you can use customized stacks with your own library. It is not even necessary to use a docker container. What is needed is the Jupyter Kernel Gateway running in contact with the Jupyter server.
Now, we turn on to the matrix side.
- look up a matrix server suited for testing, maybe your own one.
- on this server, create a user with the name of your bot.
- in another terminal, edit the _config.yml_ with the data of the matrix server that you want to use and the credentials of the bot user you have justed created. And, of course, the address of the kernel gateway:
```
version: 1.0
homeserver: amatrixserver
name: nameofyourbot
password: changeme 
gateway_address: 0.0.0.0:8888
```
- type `python3 jupybot.py`
And now invite your bot to a room. It will join and type `!nameofyourbot help` for the commands you can use.
These are some commands available:
- `!nameofyourbot startKernel nameofkernel` : it will start a kernel with the name `nameofkernel`
- `!nameofyourbot executeKernel nameof kernel
code [...]`: it will execute the code in the kernel (dot not forget: `SHIFT + ENTER` for each new line).

Since this is still a proof of concepts, the number of features is limited (command line text, string and pictures are the only output formats supported. No widget, no funny javascript) and they are few safeguards against infinite loops and other entertaining bugs.

### TODO

This is right now just a proof of concept. We want to see if such a bot can be useful for people and how. What features would be interesting, what can be integrated in the present clients,... Therefore, in the short term, we want to focus on the possibility of easy testing for users and easy contributions for people who want to add their ideas. On the mid- and long term, a lot of ideas can be realized; it will depend on the feedback.
These are just some examples.
Short term:
- proper error catching
- fallback for non supported Jupyter formats on riot.im (i.e. a lot)
- testing on termux on a tablet or smartphone
- solve the problem with nio-matrix and upload in chunks of images.
- Dockerized version

Middle term:
- use of [opsdroid](https://opsdroid.dev/) as a framework

Longer term:
- local server integrated to locally command the bot service.
- make full use of jupyter capabilities with a client suited for it (for instance a Jupyterlab plugin)