#!/bin/bash
set -euo pipefail
if [ ! -s /var/lib/postgresql/alpha/PG_VERSION ]; then
    chmod 700 /var/lib/postgresql/alpha /var/lib/postgresql/beta
    gosu postgres initdb -D /var/lib/postgresql/alpha --data-checksums --auth=trust >/var/log/commerce/init.log
    cat >>/var/lib/postgresql/alpha/postgresql.conf <<'EOF'
listen_addresses = '127.0.0.1'
wal_level = logical
wal_log_hints = on
wal_keep_size = '256MB'
max_wal_size = '512MB'
max_replication_slots = 10
max_wal_senders = 10
shared_buffers = '64MB'
archive_mode = on
archive_command = '/usr/local/bin/archive-wal %p /var/backups/wal/%f'
EOF
    gosu postgres pg_ctl -D /var/lib/postgresql/alpha -l /var/log/commerce/alpha.log -w start
    gosu postgres psql -v ON_ERROR_STOP=1 -f /srv/commerce/schema.sql
    gosu postgres pg_basebackup -h 127.0.0.1 -p 5432 -U postgres -D /var/lib/postgresql/beta -R -X stream --checkpoint=fast
    gosu postgres pg_ctl -D /var/lib/postgresql/alpha -m fast -w stop
fi
if [ ! -f /var/lib/kafka/meta.properties ]; then
    cluster_id=$(/opt/kafka/bin/kafka-storage.sh random-uuid)
    /opt/kafka/bin/kafka-storage.sh format -t "$cluster_id" -c /etc/commerce/broker.properties
fi
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
