from typing import Optional, Callable, Union, Dict, Any,Tuple
from nio.crypto import AsyncDataT

from nio import UploadResponse, UploadError
import asyncio
from nio import ErrorResponse, Api
from aiohttp.client_exceptions import ClientConnectionError

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

