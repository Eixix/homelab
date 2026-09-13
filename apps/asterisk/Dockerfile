FROM python:3.12-slim-bookworm AS prompts
RUN apt-get update && apt-get install -y --no-install-recommends sox ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir piper-tts==1.8.0
WORKDIR /voice
# Pin the public CC0 Thorsten voice; models never enter the runtime image.
ARG VOICE_REVISION=1162a9173d0ce503555aed757976b7a9912eae4c
RUN python -c 'import os, urllib.request; base = "https://huggingface.co/rhasspy/piper-voices/resolve/" + os.environ["VOICE_REVISION"] + "/de/de_DE/thorsten/high/"; [urllib.request.urlretrieve(base + name, name) for name in ("de_DE-thorsten-high.onnx", "de_DE-thorsten-high.onnx.json", "MODEL_CARD")]'
COPY prompts/ /prompts/
RUN set -eu; mkdir /sounds; for text in /prompts/*.txt; do name=$(basename "$text" .txt); \
      python -m piper -m /voice/de_DE-thorsten-high.onnx --input-file /prompts/$name.txt -f /tmp/$name.wav; \
      sox /tmp/$name.wav -r 8000 -c 1 -b 16 -e signed-integer /sounds/$name.wav gain -n -3; \
    done

FROM alpine:3.22
RUN apk add --no-cache asterisk tzdata python3 \
    && rm -rf /etc/asterisk \
    && mkdir -p /etc/asterisk /run/asterisk /var/log/asterisk /var/spool/asterisk /var/lib/asterisk/db \
    && chown -R root:root /run/asterisk /var/log/asterisk /var/spool/asterisk /var/lib/asterisk
COPY config/ /etc/asterisk/
COPY --from=prompts /sounds/ /var/lib/asterisk/sounds/custom/
COPY entrypoint.py /usr/local/bin/asterisk-entrypoint.py
COPY healthcheck.py /usr/local/bin/asterisk-healthcheck.py
COPY menu.py /usr/local/bin/menu.py
RUN chmod 755 /usr/local/bin/menu.py
ENTRYPOINT ["python3", "/usr/local/bin/asterisk-entrypoint.py"]
