ARG BASE=postgres:18-bookworm
FROM ${BASE}
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-psycopg2 supervisor curl git ripgrep less procps iproute2 postgresql-doc-18 && rm -rf /var/lib/apt/lists/*
COPY orders.py schema.sql README.md /srv/orders/
COPY supervisor.conf /etc/supervisor/supervisord.conf
COPY start-services.sh /usr/local/bin/start-services
RUN chmod 755 /usr/local/bin/start-services && mkdir -p /var/log/orders /var/lib/postgresql/alpha /var/lib/postgresql/beta && chown -R postgres:postgres /var/lib/postgresql /var/log/orders && printf '{"read_port":5432,"write_port":5432}\n' > /srv/orders/config.json
WORKDIR /srv/orders
ENTRYPOINT ["/usr/local/bin/start-services"]
