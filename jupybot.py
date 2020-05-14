from importlib import util
import asyncio
from nio import (AsyncClient, SyncResponse, RoomMessageText,Api)

import argparse
import sys
import threading
import queue
from tornado.escape import json_encode, json_decode, url_escape
from tornado.websocket import websocket_connect
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from uuid import uuid4
import json
from binascii import  a2b_base64
import base64
from nio_update import AsyncClientSpe
import sys
import yaml
from io import BytesIO
import logging
import pickle


# initialize python logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# list of commands; hardcoded for the moment
command_start_kernel = 'startKernel'
command_connect_kernel= 'connectKernel'
command_execute_kernel='executeKernel'
command_status_kernel='statusKernel'
command_help='help'

# class for communication with the Jupyter Kernel Gateway
class kernelGatewayComm:
    def __init__(self,address,matrix):
        self.matrixComm=matrix
        self.base_url = 'http://' + address
        self.base_ws_url = 'ws://' + address
        self.client = AsyncHTTPClient()
        self.kernels_ws=dict()
        try:
            with open('kernels.tmp', 'rb') as input:
                reading=pickle.load(input)
        except FileNotFoundError:
            self.kernels=dict()
        else:   
            self.kernels=reading

    async def checkKernels(self):
        response = await self.client.fetch(
            '{}/api/kernels'.format(self.base_url),
            method='GET',
            auth_username='fakeuser',
            auth_password='fakepass',
            body=None
        )
        kernel_list=json_decode(response.body)
        logging.debug(kernel_list)
        inc=0
        # check if kernel from gateway present in internal mapping list
        for kernel in kernel_list:
            if kernel['id'] not in self.kernels.values():
                self.kernels[kernel['name']+inc]=kernel('id')
                inc=inc+1
        # remove elements form internal list which are not anymore here
        kernel_list_values = [y['id'] for y in kernel_list]
        delete=[key for key, value in self.kernels.items() if value not in kernel_list_values]
        for key in delete: del self.kernels[key]

        # reconnect to kernels with websockets:
        for kernelName, kernel_id in self.kernels.items():
            ws_req = HTTPRequest(url='{}/api/kernels/{}/channels'.format(
            self.base_ws_url,
            url_escape(kernel_id)
            ),
            auth_username='fakeuser',
            auth_password='fakepass'
            )
            self.kernels_ws[kernelName] = await websocket_connect(ws_req)
            #matrix=self.matrixComm
            #await matrix.sendText(room_id,'Kernel Connected! KernelID : '+kernelName)
            logging.debug("Kernel connected: "+ kernelName )

    async def statusKernel (self,room_id):
        response = await self.client.fetch(
            '{}/api/kernels'.format(self.base_url),
            method='GET',
            auth_username='fakeuser',
            auth_password='fakepass',
            body=None
        )
        kernel_list=json_decode(response.body)
        for kernel in kernel_list:
            if kernel['id'] not in self.kernels.values():
                self.kernels[kernel['name']+inc]=kernel('id')
                inc=inc+1
        # remove elements form internal list which are not anymore here
        kernel_list_values = [y['id'] for y in kernel_list]
        delete=[key for key, value in self.kernels.items() if value not in kernel_list_values]
        for key in delete: del self.kernels[key]
        for kernel in self.kernels.keys():
           await self.matrixComm.sendText(room_id,kernel+' is connected')

    async def startKernel(self,kernelID,room_id):
        logging.debug('kernelID: '+ kernelID)
        matrix=self.matrixComm
        response = await self.client.fetch(
            '{}/api/kernels'.format(self.base_url),
            method='POST',
            auth_username='fakeuser',
            auth_password='fakepass',
            body=json_encode({'name' : 'python'})
        )
        kernel = json_decode(response.body)
        kernel_id = kernel['id']
        self.kernels[kernelID]=kernel_id
        self.kernels
        with open('kernels.tmp', 'wb') as output:
            pickle.dump(self.kernels,output)
        logging.debug(kernelID)
        
        ws_req = HTTPRequest(url='{}/api/kernels/{}/channels'.format(
                self.base_ws_url,
                url_escape(kernel_id)
            ),
            auth_username='fakeuser',
            auth_password='fakepass'
        )
        self.kernels_ws[kernelID] = await websocket_connect(ws_req)
        await matrix.sendText(room_id,'Kernel Connected! KernelID : '+kernelID)

        return kernel_id

    async def executeKernel(self,code, ws, must_return_stream,room_id):
        msg_id = uuid4().hex
        matrix=self.matrixComm
        # Send an execute request
        ws.write_message(json_encode({
            'header': {
                'username': '',
                'version': '5.0',
                'session': '',
                'msg_id': msg_id,
                'msg_type': 'execute_request'
            },
            'parent_header': {},
            'channel': 'shell',
            'content': {
                'code': code,
                'silent': False,
                'store_history': False,
                'user_expressions' : {},
                'allow_stdin' : False
            },
            'metadata': {},
            'buffers': {}
        }))
        working=True
        # Receive messages
        while working:
            msg = await ws.read_message()
            msg = json_decode(msg)
        # print(msg)
            msg_type = msg['msg_type']
            if msg_type == 'error':
                await matrix.sendText(room_id,'!!!ERROR!!!')
                await matrix.sendText(room_id,json.dumps(msg['content']))
                working=False
                return
            if msg_type=="status":
                status=msg['content']['execution_state']
                logging.debug(status)
                if status=="idle":
                    working=False
    #       parent_msg_id = msg['parent_header']['msg_id']
    #       if True:  # parent_msg_id == msg_id:
            if msg_type == 'stream':
                await matrix.sendText(room_id,msg['content']['text'])
            if not must_return_stream:
                return
            if (msg_type=="display_data") and ('image/png' in msg['content']['data']):
    #            print('Image received from Kernel')
                img=BytesIO(base64.b64decode(msg['content']['data']['image/png']))
                logging.debug(sys.getsizeof(img))
    #            img=msg['content']['data']['image/png']
                imgcall=lambda int1,int2: img
                uploadresponse=await matrix.async_client.upload(imgcall,'image/png')
                logging.debug(uploadresponse)
                uri=uploadresponse[0].content_uri
                content = {"body": "this is an image","msgtype": "m.image","mimetype":"image/png","url":uri}
                response=await matrix.async_client.room_send(room_id,'m.room.message',content)
            if (msg_type=="execute_result") and ('text/html' in msg['content']['data']):
                await matrix.sendHTML(room_id,msg['content']['data']['text/html'])
            logging.debug(msg)

class synapseComm:
    def __init__(self,homeServer,nameBot): 
        self.async_client = AsyncClientSpe('https://'+homeServer, nameBot,ssl=False)

    async def startComm(self,passwordBot):
        response = await self.async_client.login(passwordBot)
        logging.debug(response)


    async def sendText(self,room_id, response_body):
        content = {"body": response_body,"msgtype": "m.text"}
        response=await self.async_client.room_send(room_id,'m.room.message',content)

    async def sendHTML(self,room_id, response_body):
        content = {"body": response_body,"format": "org.matrix.custom.html","formatted_body":response_body,"msgtype": "m.text"}
        response=await self.async_client.room_send(room_id,'m.room.message',content)
    
async def print_help(matrixClient,room_id):
    text='startKernel kernelID -> start a new Kernel and give name kernelID\n \
        statusKernel -> list of runnign kernels and corresponding IDs \n \
        connectKernel kernelID ->  or connect to an existing Kernel with kernelID \
        executeKernel kernelID -> execute commands in the kernel with kernelID \n \
        help -> you are here \
        '
    resp=await matrixClient.sendText(room_id,text)

async def main():
    # loading config
    file=open('config.yml','r')
    config=yaml.load(file)
    homeServer=config['homeserver']
    nameBot=config['name']
    passwordBot=config['password']
    gatewayAdress=config['gateway_address']
    logging.debug(homeServer)
    logging.debug(passwordBot)

    command_init='!'+nameBot
# communication with matrix serve
    synapse=synapseComm(homeServer,nameBot)
    await synapse.startComm(passwordBot)
    #response=await synapse.async_client.join(room_id)
    sync_response = await synapse.async_client.sync(3000)
    if len(sync_response.rooms.join) > 0:
        joins = sync_response.rooms.join
        for room_id in joins:
            await synapse.sendText(room_id,nameBot+' online!')  
# starting communication with Kernel Gateway
    kernelComm=kernelGatewayComm(gatewayAdress, synapse)
    await kernelComm.checkKernels() # check Kernels which are already running on gateway
    while (True):
        sync_response = await synapse.async_client.sync(3000)
        if len(sync_response.rooms.join) > 0:
            joins = sync_response.rooms.join
            for room_id in joins:
                    for event in joins[room_id].timeline.events:
                        if isinstance(event, RoomMessageText):
                            body=event.body.split('\n',1)
                            inputText=body[0].split(' ')
                            if inputText[0]!=command_init:
                                break
                            command=inputText[1]
                            logging.debug('command received from matrix: '+command)
                            if command==command_start_kernel:
                                logging.debug('start Kernel')
                                kernelID=inputText[2]
                                kernel_id=await kernelComm.startKernel(kernelID,room_id)
                            if command==command_execute_kernel:
                                logging.debug('execute Kernel')
                                kernelID=inputText[2]
                                code=body[1]
                                logging.debug(code)
                                await kernelComm.executeKernel(code,kernelComm.kernels_ws[kernelID], True,room_id)
                            if command==command_help:
                                print_help(synapse,room_id)
                            if command==command_status_kernel:
                                logging.debug('asking for kernel status')
                                await kernelComm.statusKernel(room_id)
asyncio.run(main())
