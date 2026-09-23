#!/bin/bash
set -euo pipefail
if [ ! -s /var/lib/postgresql/alpha/PG_VERSION ]; then
    chmod 700 /var/lib/postgresql/alpha /var/lib/postgresql/beta
    gosu postgres initdb -D /var/lib/postgresql/alpha --data-checksums --auth=trust >/var/log/orders/init.log
    cat >>/var/lib/postgresql/alpha/postgresql.conf <<'EOF'
listen_addresses = '127.0.0.1'
wal_log_hints = on
wal_keep_size = '128MB'
max_wal_size = '256MB'
shared_buffers = '32MB'
EOF
    gosu postgres pg_ctl -D /var/lib/postgresql/alpha -l /var/log/orders/alpha.log -w start
    gosu postgres psql -v ON_ERROR_STOP=1 -f /srv/orders/schema.sql
    gosu postgres pg_basebackup -h 127.0.0.1 -p 5432 -U postgres -D /var/lib/postgresql/beta -R -X stream --checkpoint=fast
    gosu postgres pg_ctl -D /var/lib/postgresql/alpha -m fast -w stop
fi
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
