from importlib import util
import asyncio
from nio import (AsyncClient, SyncResponse, RoomMessageText,Api)
from nio.client.async_client import logged_in
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

async def startKernel(room_id):
    address="0.0.0.0:8888"
    kernel_id=0
    base_url = 'http://' + address
    base_ws_url = 'ws://' + address

    client = AsyncHTTPClient()
    if not kernel_id:
        response = await client.fetch(
            '{}/api/kernels'.format(base_url),
            method='POST',
            auth_username='fakeuser',
            auth_password='fakepass',
            body=json_encode({'name' : 'python'})
        )
        kernel = json_decode(response.body)
        kernel_id = kernel['id']

    ws_req = HTTPRequest(url='{}/api/kernels/{}/channels'.format(
            base_ws_url,
            url_escape(kernel_id)
        ),
        auth_username='fakeuser',
        auth_password='fakepass'
    )
    ws = await websocket_connect(ws_req)
    print(ws)
    await sendText(room_id,'Kernel Connected!')
    return ws, kernel_id

async def executeKernel(code, ws, must_return_stream,room_id):
    msg_id = uuid4().hex
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
            await sendText(room_id,'!!!ERROR!!!')
            await sendText(room_id,json.dumps(msg['content']))
            working=False
            return
        if msg_type=="status":
            status=msg['content']['execution_state']
            print(status)
            if status=="idle":
                working=False
 #       parent_msg_id = msg['parent_header']['msg_id']
 #       if True:  # parent_msg_id == msg_id:
        if msg_type == 'stream':
            await sendText(room_id,msg['content']['text'])
        if not must_return_stream:
            return
        if (msg_type=="display_data") and ('image/png' in msg['content']['data']):
#            print('Image received from Kernel')
            img=BytesIO(base64.b64decode(msg['content']['data']['image/png']))
            print(sys.getsizeof(img))
#            img=msg['content']['data']['image/png']
            imgcall=lambda int1,int2: img
            uploadresponse=await async_client.upload(imgcall,'image/png')
            print(uploadresponse)
            uri=uploadresponse[0].content_uri
            content = {"body": "this is an image","msgtype": "m.image","mimetype":"image/png","url":uri}
            response=await async_client.room_send(room_id,'m.room.message',content)

async def sendText(room_id, response_body):
    content = {"body": response_body,"msgtype": "m.text"}
    response=await async_client.room_send(room_id,'m.room.message',content)
    

async def main():
    file=open('config.yml','r')
    config=yaml.load(file)
    command_start_kernel = 'startKernel'
    command_execute_kernel='executeKernel'
    homeserver=config['homeserver']
    nameBot=config['name']
    passwordBot=config['password']
    command_init='!'+nameBot
    async_client = AsyncClientSpe(
    response = await async_client.login(passwordBot))
    print(response)
    response=await async_client.join(room_id)
    await sendText(room_id,nameBot+' online!')
    sync_response = await async_client.sync(3000)
    while (True):
        sync_response = await async_client.sync(3000)
        if len(sync_response.rooms.join) > 0:
            joins = sync_response.rooms.join
            for room_id in joins:
                    for event in joins[room_id].timeline.events:
                        if isinstance(event, RoomMessageText) and event.body.split(' ',1)[0]==command_init:
                            print('message received')
                            rest=event.body.split(' ',1)[1]
                            command=rest.split()[0]
                            if command==command_start_kernel:
                                ws,kernel_id=await startKernel(room_id)
                            if command==command_execute_kernel:
                                print('execute Kernel')
                                code=rest.split(maxsplit=1)[1]
                                print(rest)
                                await executeKernel(code,ws, True,room_id)
asyncio.run(main())
