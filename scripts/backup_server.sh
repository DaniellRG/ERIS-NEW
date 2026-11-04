#!/bin/bash
# Backup script: syncs Eris data from ZimaOS server to local backup
# Run via cron: */10 * * * * /home/soul/ERIS-NEW/scripts/backup_server.sh

SERVER="daniel@100.69.172.124"
REMOTE_DIR="/opt/eris"
LOCAL_BACKUP="/home/soul/ERIS-NEW/backup_server"
PASSWORD="dsoul76123267890"

mkdir -p "$LOCAL_BACKUP"

export SSHPASS="$PASSWORD"
rsync -avz --delete \
  -e "sshpass -e ssh -o StrictHostKeyChecking=no" \
  "$SERVER:$REMOTE_DIR/data/" "$LOCAL_BACKUP/data/" 2>/dev/null

rsync -avz --delete \
  -e "sshpass -e ssh -o StrictHostKeyChecking=no" \
  "$SERVER:$REMOTE_DIR/memory/" "$LOCAL_BACKUP/memory/" 2>/dev/null

rsync -avz --delete \
  -e "sshpass -e ssh -o StrictHostKeyChecking=no" \
  "$SERVER:$REMOTE_DIR/config/" "$LOCAL_BACKUP/config/" 2>/dev/null

echo "Backup completed: $(date)" >> "$LOCAL_BACKUP/backup.log"
