# Deploy to Archbook

Skill for deploying files and running commands on Archbook server (192.168.0.10).

## Context

- **Server**: Archbook (192.168.0.10)
- **SSH Port**: 2222
- **User**: sergey
- **SSH Key**: ~/.ssh/archbook_key
- **Ansible Inventory**: ansible/inventory/hosts.yml

## Available Operations

### Copy File to Server
```bash
ansible archbook -i ansible/inventory/hosts.yml \
  -m copy -a "src=LOCAL_PATH dest=REMOTE_PATH"
```

### Run Command on Server
```bash
ansible archbook -i ansible/inventory/hosts.yml \
  -m shell -a "COMMAND"
```

### Apply Database Migration
```bash
# 1. Copy migration file
ansible archbook -i ansible/inventory/hosts.yml \
  -m copy -a "src=migrations/XXX.sql dest=/tmp/migration.sql"

# 2. Apply migration
ansible archbook -i ansible/inventory/hosts.yml \
  -m shell -a "psql -U postgres -d price_scout -f /tmp/migration.sql"
```

### Restart Services
```bash
# User-level services (no sudo needed)
ansible archbook -i ansible/inventory/hosts.yml \
  -m shell -a "systemctl --user restart price-scout-bot.service"

# System services (NOPASSWD configured for moex-telegram-bot only)
ansible archbook -i ansible/inventory/hosts.yml \
  -m systemd -a "name=moex-telegram-bot.service state=restarted" --become
```

## Instructions

When user asks to deploy or run commands on Archbook:

1. Always use the Ansible inventory at `ansible/inventory/hosts.yml`
2. For file copy operations, use the `copy` module
3. For shell commands, use the `shell` module
4. For migrations: copy to /tmp first, then apply with psql
5. Check command output for errors

## Example Usage

User: "Apply migration 008"

Steps:
1. Copy migration file:
   ```bash
   ansible archbook -i ansible/inventory/hosts.yml \
     -m copy -a "src=migrations/008_arbitrage_analytics.sql dest=/tmp/migration.sql"
   ```

2. Apply to database:
   ```bash
   ansible archbook -i ansible/inventory/hosts.yml \
     -m shell -a "psql -U postgres -d price_scout -f /tmp/migration.sql"
   ```

3. Verify tables created:
   ```bash
   ansible archbook -i ansible/inventory/hosts.yml \
     -m shell -a "psql -U postgres -d price_scout -c '\dt arbitrage*'"
   ```
