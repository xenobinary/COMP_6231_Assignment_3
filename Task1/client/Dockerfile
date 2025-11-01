FROM ozxx33/fileserver-base
WORKDIR /usr/src/app
COPY . .
ENV SERVER_IP=server
ENV SERVER_PORT=65432
CMD ["python", "./client.py"]