FROM jupyter/scipy-notebook

# install the kernel gateway
RUN pip install jupyter_kernel_gateway

# run kernel gateway on container start, not notebook server
EXPOSE 8888

# the last argument is very important, otherwise you can not list the running kernels - check security issues
CMD ["jupyter", "kernelgateway", "--KernelGatewayApp.ip=0.0.0.0", "--KernelGatewayApp.port=8888", "--JupyterWebsocketPersonality.list_kernels=True"]

