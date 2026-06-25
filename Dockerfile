FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        iproute2 \
        procps \
        util-linux \
        pciutils \
        smartmontools \
        nvme-cli \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/flask_app.py /app/flask_app.py
COPY app/brain /app/brain
COPY app/assets /app/assets

EXPOSE 8601

CMD ["python", "/app/flask_app.py"]
