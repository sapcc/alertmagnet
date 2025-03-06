FROM keppel.eu-de-1.cloud.sap/ccloud-dockerhub-mirror/library/alpine:3.21
LABEL source_repository="https://github.com/sapcc/alertmagnet"

RUN apk upgrade --no-cache --no-progress \
  && apk add --no-cache --no-progress python3 bash git py3-setuptools

RUN git clone https://github.com/sapcc/alertmagnet.git
WORKDIR /alertmagnet

RUN python3 setup.py install 

ENTRYPOINT python3 main.py
