# JupyBot
## we can say it is a very early zeta version

Welcome on the README page of the JupyBOT.
This is a bot suited for the matrix.org federation of servers. It can be used with whatever client (for instance riot.im') available for the network.

The purpose of the bot is to provide a link with Jupyter kernels running either on your local computer or somewhere else on a server. 
You can access your kernels through the bot with the chat interface. The kernels will answer to your commands through the same interface.

### Requirements with the present version
It corresponds to the version I have tested. It may work in rather different conditions as well provided minor modifications
- Tested on Debian 10
- Python 3
- Docker
- Jupyter stack with Jupyter Kernel Gateway. The stack is provided in a docker container.

### Start up
There are some steps involved, not everything is not yet automated. The focus now is on the bot working and checking what users need.
We start the Jupyter kernel gateway and the associated Jupyter server:
- clone the present repository from github
- go into the _gateway_ directory
- launch start.sh
This is it for the Jupyter part. Of course, you can use customized stacks with your own library. It is not even necessary to use a docker container. What is needed is the Jupyter Kernel Gateway running in contact with the Jupyter server.
Now, we turn on to the matrix side.
- look up a matrix server suited for testing, maybe your own one.
- on this server, create a user with the name of your bot.
- in another terminal, edit the config.yml with the data of the matrix server that you want to use and the credentials of the bot user you have justed created. And, of course, the address of the kernel gateway
- type python3 jupybot.py
And now invite your bot to a room. It will join and type !nameofyourbot help for the commands you can use.
