FROM alpine:latest AS alpine

FROM docker.n8n.io/n8nio/n8n:latest

USER root

COPY --from=alpine /sbin/apk /sbin/apk
COPY --from=alpine /usr/lib/libapk.so* /usr/lib/

RUN apk add --no-cache \
    python3 \
    py3-pip \
    pango \
    cairo \
    font-noto \
    libffi-dev \
    py3-cffi \
    gdk-pixbuf \
    libxml2 \
    libxslt

WORKDIR /data/PythonN8n

COPY requirements.txt .

RUN pip3 install \
    --break-system-packages \
    --no-cache-dir \
    -r requirements.txt

COPY . /data/PythonN8n

RUN chown -R node:node /data/PythonN8n

USER node