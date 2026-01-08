# Price Scout - Claude Code Instructions

## Archbook Server Access Rules

**CRITICAL**: For ALL operations with Archbook server (192.168.0.10), use ONLY Ansible modules.

### Required Approach

**NEVER use:**
- `ssh` directly
- `scp` for file transfers
- `rsync` for syncing

**ALWAYS use:**
- `ansible ... -m copy` for file transfers
- `ansible ... -m shell` for running commands
- `ansible ... -m synchronize` for directory sync (if needed)

### Ansible Inventory

Always use the project inventory:
```bash
ansible archbook -i ansible/inventory/hosts.yml ...
```

### Common Operations

#### Copy Single File
```bash
ansible archbook -i ansible/inventory/hosts.yml \
  -m copy -a "src=LOCAL_PATH dest=REMOTE_PATH"
```

#### Sync Directory (like rsync)
```bash
ansible archbook -i ansible/inventory/hosts.yml \
  -m synchronize -a "src=LOCAL_DIR/ dest=REMOTE_DIR/ delete=yes rsync_opts='--exclude=target,--exclude=.git,--exclude=venv'"
```

#### Run Command
```bash
ansible archbook -i ansible/inventory/hosts.yml \
  -m shell -a "COMMAND"
```

#### Build on Server
```bash
ansible archbook -i ansible/inventory/hosts.yml \
  -m shell -a "cd /home/sergey/price_scout && cargo build --release --bin BINARY_NAME"
```

#### Restart Service
```bash
# User-level services
ansible archbook -i ansible/inventory/hosts.yml \
  -m shell -a "systemctl --user restart SERVICE_NAME"

# System services with NOPASSWD
ansible archbook -i ansible/inventory/hosts.yml \
  -m systemd -a "name=SERVICE_NAME state=restarted" --become
```

### Database Operations

#### Apply Migration
```bash
# Copy migration
ansible archbook -i ansible/inventory/hosts.yml \
  -m copy -a "src=migrations/XXX.sql dest=/tmp/migration.sql"

# Apply
ansible archbook -i ansible/inventory/hosts.yml \
  -m shell -a "psql -U postgres -d price_scout -f /tmp/migration.sql"
```

#### Query Database
```bash
ansible archbook -i ansible/inventory/hosts.yml \
  -m shell -a "psql -U postgres -d price_scout -c 'SELECT ...'"
```

### Deployment Workflow

1. **Sync code** (use synchronize module)
2. **Build on server** (shell module with cargo build)
3. **Restart service** (shell module with systemctl --user)
4. **Verify** (shell module to check status/logs)

### Server Details

| Parameter | Value                       |
|-----------|-----------------------------|
| Host      | 192.168.0.10                |
| SSH Port  | 2222                        |
| User      | sergey                      |
| SSH Key   | ~/.ssh/archbook_key         |
| Inventory | ansible/inventory/hosts.yml |
