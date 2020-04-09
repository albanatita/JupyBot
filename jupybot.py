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
from nio import ErrorResponse
from aiohttp.client_exceptions import ClientConnectionError
import sys
from typing import Optional, Callable, Union, Dict, Any,Tuple
from nio.crypto import AsyncDataT
from io import BytesIO
from nio import UploadResponse, UploadError

DataProvider = Callable[[int, int], AsyncDataT]

class AsyncClientSpe(AsyncClient):

    @logged_in
    async def upload(
        self,
        data_provider: DataProvider,
        content_type:  str                       = "application/octet-stream",
        filename:      Optional[str]             = None,
        encrypt:       bool                      = False,
        monitor = None,
    ) -> Tuple[Union[UploadResponse, UploadError], Optional[Dict[str, Any]]]:

        method, path, _ = Api.upload(self.access_token, filename)
        got_429 = 0
        max_429 = self.config.max_limit_exceeded

        got_timeouts = 0
        max_timeouts = self.config.max_timeouts
        decryption_dict: Dict[str, Any] = {}
        data =data_provider(got_429, got_timeouts)
        headers = {"Content-Type": content_type,
       #        "Content-Length": str(sys.getsizeof(data))
        } if content_type else {
                  "Content-Type": "application/json"
        }
        trace_context = monitor
        timeout=0
        response_data=None
        response_class=UploadResponse
        while True:
            try:
                print('sending request)')
                transport_resp = await self.send(
                    method, path, data, headers, trace_context, timeout,
                )
                print(transport_resp)

                resp = await self.create_matrix_response(
                    response_class,
                    transport_resp,
                    response_data,
                )
                print(type(resp))
                if isinstance(resp, ErrorResponse) and resp.retry_after_ms:
                    got_429 += 1
                    print('err..')
                    if max_429 is not None and got_429 > max_429:
                        print( max_429)
                        break

                    await self.run_response_callbacks([resp])
                    await asyncio.sleep(resp.retry_after_ms / 1000)
                else:
                    break

            except (ClientConnectionError, TimeoutError, asyncio.TimeoutError):
                got_timeouts += 1

                if max_timeouts is not None and got_timeouts > max_timeouts:
                    raise

                wait = await self.get_timeout_retry_wait_time(got_timeouts)
                await asyncio.sleep(wait)

        await self.receive_response(resp)
        return (resp,None)

command_init='!jupybot'
command_start_kernel = 'startKernel'
command_execute_kernel='executeKernel'
room_id='!zSHNwIxpmqkwFKUuhu:matrix.alkemata.com'

async_client = AsyncClientSpe(
    "https://matrix.alkemata.com", "JupyBot1",ssl=False)

async def startKernel():
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

async def executeKernel(code, ws, must_return_stream):
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
    response = await async_client.login("changeme")
    print(response)
    response=await async_client.join(room_id)
    await sendText(room_id,'JupyBot1 online!')
    sync_response = await async_client.sync(3000)
    while (True):
        sync_response = await async_client.sync(3000)
        if len(sync_response.rooms.join) > 0:
            joins = sync_response.rooms.join
            for event in joins[room_id].timeline.events:
                if isinstance(event, RoomMessageText) and event.body.split(' ',1)[0]==command_init:
                    print('message received')
                    rest=event.body.split(' ',1)[1]
                    command=rest.split()[0]
                    if command==command_start_kernel:
                        ws,kernel_id=await startKernel()
                    if command==command_execute_kernel:
                        print('execute Kernel')
                        code=rest.split(maxsplit=1)[1]
                        print(rest)
                        await executeKernel(code,ws, True)
asyncio.run(main())
