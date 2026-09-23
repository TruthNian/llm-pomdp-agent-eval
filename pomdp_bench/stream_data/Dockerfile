ARG CONNECT=quay.io/debezium/connect:3.2.1.Final
ARG POSTGRES=postgres:17-bookworm
FROM ${CONNECT} AS kafka
FROM ${POSTGRES}
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-psycopg2 python3-kafka supervisor curl git ripgrep less procps iproute2 default-jre-headless postgresql-doc-17 && rm -rf /var/lib/apt/lists/*
COPY --from=kafka /kafka /opt/kafka
COPY service.py schema.sql README.md CARRIER.md /srv/commerce/
COPY broker.properties connect.properties connector.json log4j2.properties /etc/commerce/
COPY supervisor.conf /etc/supervisor/supervisord.conf
COPY start-services.sh /usr/local/bin/start-commerce
COPY archive-wal.sh /usr/local/bin/archive-wal
RUN chmod 755 /usr/local/bin/start-commerce /usr/local/bin/archive-wal && mkdir -p /var/log/commerce /var/lib/kafka /var/lib/postgresql/alpha /var/lib/postgresql/beta /var/backups/wal && chown -R postgres:postgres /var/lib/postgresql /var/log/commerce /var/backups/wal && printf '{"port":5432,"carrier":"http://127.0.0.1:8099","topic":"commerce.public.outbox","group":"commerce-dispatch"}\n' > /etc/commerce/application.json
WORKDIR /srv/commerce
ENTRYPOINT ["/usr/local/bin/start-commerce"]
