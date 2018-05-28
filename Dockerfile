FROM python:3.7-stretch

COPY . /usr/src/app/

RUN mkdir -p /usr/src/build && \
    cd /usr/src/build && \
    pip3 install --upgrade pip setuptools wheel cython && \
    pip3 install -r /usr/src/app/requirements.txt && \
    /usr/src/app/script/install-coap-client.sh && \
    python /usr/src/app/setup.py install 

RUN python3 -m pip install paho-mqtt

COPY ./entrypoint.py /usr/src/app/entrypoint.py

WORKDIR /usr/src/app
ENV LANG=C.UTF-8
CMD /bin/bash
