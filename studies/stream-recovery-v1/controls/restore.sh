set -euo pipefail
test ! -e /var/lib/postgresql/salvage
install -d -o postgres -g postgres -m 700 /var/lib/postgresql/salvage
cp -a /var/backups/commerce-base/. /var/lib/postgresql/salvage/
cat >> /var/lib/postgresql/salvage/postgresql.auto.conf <<'EOF'
restore_command = 'cp /var/backups/wal/%f %p'
recovery_target_timeline = '1'
EOF
touch /var/lib/postgresql/salvage/recovery.signal
chown -R postgres:postgres /var/lib/postgresql/salvage
gosu postgres pg_ctl -D /var/lib/postgresql/salvage -l /var/log/commerce/salvage.log -o '-p 5440 -c archive_mode=off' -t 60 -w start
psql -h 127.0.0.1 -p 5440 -U postgres -d commerce -v ON_ERROR_STOP=1 -c 'SELECT count(*) AS recovered_orders FROM orders; SELECT count(*) AS recovered_events FROM outbox;'
