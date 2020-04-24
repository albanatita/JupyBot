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

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

class kernelGatewayComm:
    def __init__(self,address,matrixComm):
        self.address=address
        self.matrixComm=matrixComm
        self.kernels=dict()

    async def startKernel(self,room_id,kernelID):
        address=self.address
        matrix=self.matrixComm
        base_url = 'http://' + address
        base_ws_url = 'ws://' + address
        logging.debug('kernelID: '+ kernelID)
        client = AsyncHTTPClient()
        response = await client.fetch(
            '{}/api/kernels'.format(base_url),
            method='POST',
            auth_username='fakeuser',
            auth_password='fakepass',
            body=json_encode({'name' : 'python'})
        )
        kernel = json_decode(response.body)
        kernel_id = kernel['id']
        kernel_id=self.kernels[kernelID]
        logging.debug(kernelID)
        kernels

        ws_req = HTTPRequest(url='{}/api/kernels/{}/channels'.format(
                base_ws_url,
                url_escape(kernel_id)
            ),
            auth_username='fakeuser',
            auth_password='fakepass'
        )
        ws = await websocket_connect(ws_req)
        await matrix.sendText(room_id,'Kernel Connected! KernelID : '+kernelID)
        return ws, kernel_id

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
            #if (msg_type=="display_data") and ('html' in msg['content']['data']):

class synapseComm:
    def __init__(self,homeServer,nameBot): 
        self.async_client = AsyncClientSpe('https://'+homeServer, nameBot,ssl=False)

    async def startComm(self,passwordBot):
        response = await self.async_client.login(passwordBot)
        logging.debug(response)


    async def sendText(self,room_id, response_body):
        content = {"body": response_body,"msgtype": "m.text"}
        response=await self.async_client.room_send(room_id,'m.room.message',content)
    
def print_help(matrixClient,room_id):
    text='startKernel kernelID -> start a new Kernel and give name kernelID\n \
        connectKernel kernelID ->  or connect to an existing Kernel with kernelID \
        executeKernel kernelID -> execute commands in the kernel with kernelID \n \
        help -> you are here \
        '
    matrixClient.sendText(room_id,text)

async def main():
    file=open('config.yml','r')
    config=yaml.load(file)
    command_start_kernel = 'startKernel'
    command_connect_kernel= 'connectKernel'
    command_execute_kernel='executeKernel'
    command_help='help'
    homeServer=config['homeserver']
    nameBot=config['name']
    passwordBot=config['password']
    gatewayAdress=config['gateway_address']
    logging.debug(homeServer)
    logging.debug(passwordBot)
    command_init='!'+nameBot
    synapse=synapseComm(homeServer,nameBot)
    await synapse.startComm(passwordBot)
    #response=await synapse.async_client.join(room_id)
    sync_response = await synapse.async_client.sync(3000)
    if len(sync_response.rooms.join) > 0:
        joins = sync_response.rooms.join
        for room_id in joins:
            await synapse.sendText(room_id,nameBot+' online!')  

    kernelComm=kernelGatewayComm(gatewayAdress, synapse)
    ## finish HERE!!!!
    while (True):
        sync_response = await synapse.async_client.sync(3000)
        if len(sync_response.rooms.join) > 0:
            joins = sync_response.rooms.join
            for room_id in joins:
                    for event in joins[room_id].timeline.events:
                        if isinstance(event, RoomMessageText):
                            body=event.body.split('\n',1)
                            inputText=body[0].split(' ',1)
                            if inputText[0]!=command_init:
                                break
                            command=inputText[1]
                            logging.debug('command received from matrix')
                            if command==command_start_kernel:
                                logging.debug('start Kernel')
                                kernelID=inputText[2]
                                ws,kernel_id=await kernelComm.startKernel(room_id,kernelID)
                            if command==command_execute_kernel:
                                logging.debug('execute Kernel')
                                code=body[1]
                                logging.debug(code)
                                await kernelComm.executeKernel(code,ws, True,room_id)
                            if command==command_help:
                                print_help(synapse,room_id)
asyncio.run(main())
