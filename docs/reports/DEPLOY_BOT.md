# Telegram Bot Deployment Guide

Quick deployment guide for Price Scout Telegram Bot to Archbook server (192.168.0.10).

## Prerequisites

- [+] API server running on port 3000
- [+] PostgreSQL with product data
- [+] Telegram bot token from @BotFather
- [+] SSH access to Archbook

## Quick Deployment

### Step 1: Build Release Binary

```bash
# On local machine
cd /home/ryazanov/Development/price_scout

# Build optimized binary
cargo build --release --bin price-scout-bot

# Verify binary
ls -lh target/release/price-scout-bot
# Expected: ~3-4 MB
```

### Step 2: Copy to Archbook

```bash
# Copy binary
rsync -avz -e "ssh -i ~/.ssh/archbook_key -p 2222" \
  target/release/price-scout-bot \
  sergey@192.168.0.10:/home/sergey/price_scout/target/release/

# Copy service file
rsync -avz -e "ssh -i ~/.ssh/archbook_key -p 2222" \
  config/price-scout-bot.service \
  sergey@192.168.0.10:/home/sergey/price_scout/config/
```

### Step 3: Install Systemd Service

```bash
# SSH to Archbook
ssh -i ~/.ssh/archbook_key -p 2222 sergey@192.168.0.10

# Copy service file to systemd
sudo cp /home/sergey/price_scout/config/price-scout-bot.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable price-scout-bot.service

# Start service
sudo systemctl start price-scout-bot.service
```

### Step 4: Verify Deployment

```bash
# Check service status
sudo systemctl status price-scout-bot.service
# Expected: "active (running)"

# View logs
sudo journalctl -u price-scout-bot.service -f

# Expected log output:
# "Bot started successfully"
# "Connected to API: http://localhost:3000"
# "Bot listening for commands"
```

### Step 5: Test Bot

1. **Open Telegram**
2. **Search for bot**: `@price_scout_majobot`
3. **Send test commands**:
   ```
   /start
   /help
   /search MacBook
   ```

## Configuration

### Bot Token

**Current Bot:**
- Username: `@price_scout_majobot`
- Token: `8165489394:AAEh2lZnd0V8c9lGp7xoY6CW8PHnB2pIZfM`

**Update Token:**
Edit `/etc/systemd/system/price-scout-bot.service`:
```ini
Environment="TELOXIDE_TOKEN=<new_token>"
```

Then restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart price-scout-bot.service
```

### API URL

**Default:** `http://localhost:3000`

**Change API URL:**
Edit service file:
```ini
Environment="PRICE_SCOUT_API_URL=http://192.168.0.10:3000"
```

## Service Management

### Start/Stop/Restart

```bash
# Start bot
sudo systemctl start price-scout-bot.service

# Stop bot
sudo systemctl stop price-scout-bot.service

# Restart bot
sudo systemctl restart price-scout-bot.service

# Check status
sudo systemctl status price-scout-bot.service
```

### View Logs

```bash
# Live logs (tail -f)
sudo journalctl -u price-scout-bot.service -f

# Last 100 lines
sudo journalctl -u price-scout-bot.service -n 100

# Logs since boot
sudo journalctl -u price-scout-bot.service -b

# Logs for specific time
sudo journalctl -u price-scout-bot.service --since "1 hour ago"
```

### Enable/Disable Auto-Start

```bash
# Enable (start on boot)
sudo systemctl enable price-scout-bot.service

# Disable (don't start on boot)
sudo systemctl disable price-scout-bot.service

# Check if enabled
systemctl is-enabled price-scout-bot.service
```

## Troubleshooting

### Issue 1: Bot doesn't start

**Error:** `Failed to start price-scout-bot.service`

**Check 1: Binary exists?**
```bash
ls -lh /home/sergey/price_scout/target/release/price-scout-bot
```

**Check 2: Executable permissions?**
```bash
chmod +x /home/sergey/price_scout/target/release/price-scout-bot
```

**Check 3: Logs show errors?**
```bash
sudo journalctl -u price-scout-bot.service -n 50
```

### Issue 2: Can't connect to API

**Error:** `Failed to connect to API`

**Check 1: API running?**
```bash
sudo systemctl status price-scout-api.service
curl http://localhost:3000/health
```

**Check 2: Firewall blocking?**
```bash
sudo ufw status
```

**Check 3: Correct API URL?**
```bash
grep PRICE_SCOUT_API_URL /etc/systemd/system/price-scout-bot.service
```

### Issue 3: Bot token invalid

**Error:** `Unauthorized: Bot token is invalid`

**Solution:**
1. Verify token in service file:
   ```bash
   grep TELOXIDE_TOKEN /etc/systemd/system/price-scout-bot.service
   ```
2. Get new token from @BotFather:
   - Message @BotFather on Telegram
   - Send `/token`
   - Select your bot
   - Copy new token
3. Update service file and restart

### Issue 4: Bot responds slowly

**Symptom:** Commands take 5-10 seconds to respond

**Check 1: API response time**
```bash
time curl http://localhost:3000/api/stores
```

**Check 2: Database performance**
```bash
psql postgresql://postgres@localhost:5432/price_scout -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"
```

**Check 3: Resource usage**
```bash
# Bot memory usage
ps aux | grep price-scout-bot

# System resources
free -h
df -h
```

## Updating the Bot

### Deploy New Version

```bash
# 1. Build new version locally
cargo build --release --bin price-scout-bot

# 2. Copy to Archbook
rsync -avz -e "ssh -i ~/.ssh/archbook_key -p 2222" \
  target/release/price-scout-bot \
  sergey@192.168.0.10:/home/sergey/price_scout/target/release/

# 3. Restart service
ssh -i ~/.ssh/archbook_key -p 2222 sergey@192.168.0.10 \
  "sudo systemctl restart price-scout-bot.service"

# 4. Verify
ssh -i ~/.ssh/archbook_key -p 2222 sergey@192.168.0.10 \
  "sudo systemctl status price-scout-bot.service"
```

### Rollback to Previous Version

```bash
# Backup current binary before updates
ssh -i ~/.ssh/archbook_key -p 2222 sergey@192.168.0.10
cp /home/sergey/price_scout/target/release/price-scout-bot \
   /home/sergey/price_scout/target/release/price-scout-bot.backup.$(date +%Y%m%d)

# To rollback
cp /home/sergey/price_scout/target/release/price-scout-bot.backup.20260105 \
   /home/sergey/price_scout/target/release/price-scout-bot
sudo systemctl restart price-scout-bot.service
```

## Security Notes

### Service Hardening

The systemd service includes security hardening:

- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- `ProtectSystem=strict` - Read-only system directories
- `ProtectHome=read-only` - Read-only home directory
- `ReadWritePaths=/home/sergey/price_scout/models` - Only ML models directory is writable

### Bot Token Security

**Important:**
- NEVER commit bot token to git
- NEVER share token publicly
- Rotate token periodically (monthly recommended)
- Use different tokens for dev/prod

**Rotate Token:**
1. Message @BotFather
2. Send `/revoke`
3. Select bot
4. Get new token
5. Update service file
6. Restart service

## Monitoring

### Check Bot Health

```bash
# Service uptime
systemctl show price-scout-bot.service -p ActiveEnterTimestamp

# Memory usage
systemctl show price-scout-bot.service -p MemoryCurrent

# Restart count
systemctl show price-scout-bot.service -p NRestarts
```

### Log Analysis

```bash
# Count errors in logs
sudo journalctl -u price-scout-bot.service --since "24 hours ago" | grep -i error | wc -l

# Find slow requests
sudo journalctl -u price-scout-bot.service --since "1 hour ago" | grep "took"

# User activity
sudo journalctl -u price-scout-bot.service --since "24 hours ago" | grep "Command:" | wc -l
```

## Performance Benchmarks

**Expected Performance:**

| Metric        | Value       | Notes                        |
|---------------|-------------|------------------------------|
| Startup time  | 1-2 seconds | Binary load + API connection |
| Memory usage  | 20-50 MB    | Base + teloxide runtime      |
| Response time | 100-500ms   | Command → Telegram reply     |
| API latency   | 50-300ms    | Depends on query complexity  |

**Command-Specific:**

| Command    | Response Time | Notes                  |
|------------|---------------|------------------------|
| /start     | ~100ms        | No API call            |
| /help      | ~100ms        | No API call            |
| /search    | ~200-400ms    | Database query         |
| /price     | ~200-500ms    | Multiple store queries |
| /trends    | ~300-600ms    | Aggregation query      |
| /predict   | ~500-1000ms   | Python ML subprocess   |
| /arbitrage | ~400-800ms    | Complex joins          |
| /compare   | ~300-600ms    | Analytics query        |

## Backup and Recovery

### Backup Configuration

```bash
# Backup service file
sudo cp /etc/systemd/system/price-scout-bot.service \
  /home/sergey/backups/price-scout-bot.service.$(date +%Y%m%d)

# Backup binary
cp /home/sergey/price_scout/target/release/price-scout-bot \
  /home/sergey/backups/price-scout-bot.$(date +%Y%m%d)
```

### Restore from Backup

```bash
# Restore service
sudo cp /home/sergey/backups/price-scout-bot.service.20260105 \
  /etc/systemd/system/price-scout-bot.service
sudo systemctl daemon-reload

# Restore binary
cp /home/sergey/backups/price-scout-bot.20260105 \
  /home/sergey/price_scout/target/release/price-scout-bot
chmod +x /home/sergey/price_scout/target/release/price-scout-bot

# Restart
sudo systemctl restart price-scout-bot.service
```

## Related Documentation

- **Bot User Guide**: [docs/TELEGRAM_BOT.md](docs/TELEGRAM_BOT.md)
- **API Documentation**: [docs/ANALYTICS_API.md](docs/ANALYTICS_API.md)
- **Project Dashboard**: [PROJECT_DASHBOARD.md](PROJECT_DASHBOARD.md)

---

**Status**: ✅ Ready for Deployment
**Estimated Deployment Time**: 10-15 minutes
**Recommended Deployment Window**: Off-peak hours

**Deployed By**: _________________
**Deployment Date**: _________________
**Verification Signature**: _________________
