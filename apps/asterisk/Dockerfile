FROM alpine:3.22 AS prompts
RUN apk add --no-cache espeak-ng sox
COPY prompts/ /prompts/
RUN mkdir /sounds && for name in greeting test invalid goodbye; do \
      espeak-ng -v de -s 145 -f /prompts/$name.txt -w /tmp/$name.wav && \
      sox /tmp/$name.wav -r 8000 -c 1 -b 16 -e signed-integer /sounds/$name.wav; \
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
ENTRYPOINT ["python3", "/usr/local/bin/asterisk-entrypoint.py"]
