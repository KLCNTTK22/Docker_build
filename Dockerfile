FROM alpine:latest AS alpine

FROM docker.n8n.io/n8nio/n8n:latest

USER root

COPY --from=alpine /sbin/apk /sbin/apk
COPY --from=alpine /usr/lib/libapk.so* /usr/lib/

# CÀI ĐẶT THÊM: Các thư viện bổ trợ cho PDF (Pango, Cairo, Fonts)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    pango \
    cairo \
    font-noto \
    libffi-dev \
    py3-cffi

WORKDIR /data/PythonN8n

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /data/PythonN8n
RUN chown -R node:node /data/PythonN8n

USER node