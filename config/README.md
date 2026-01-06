# Price Scout Configuration Files

## Systemd Service Files

This directory contains systemd service and timer files for automated deployment.

### Files

| File                              | Description                                      |
|-----------------------------------|--------------------------------------------------|
| price-scout-worker.service        | Background worker (continuous processing)        |
| price-scout-scheduler.service     | Scheduler (one-shot job enqueuing)               |
| price-scout-scheduler.timer       | Timer for scheduler (every 10 minutes)           |
| stores.json                       | Store configuration (legacy, use PostgreSQL)     |

### Deployment Options

#### Option 1: Continuous Worker (Recommended for Production)

The worker runs continuously and polls for jobs every 10 minutes.

```bash
# Copy service file
sudo cp config/price-scout-worker.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable price-scout-worker
sudo systemctl start price-scout-worker

# Check status
sudo systemctl status price-scout-worker

# View logs
sudo journalctl -u price-scout-worker -f
```

#### Option 2: Timer-Based Scheduler (Recommended for Development)

The scheduler runs every 10 minutes via systemd timer.

```bash
# Copy service and timer files
sudo cp config/price-scout-scheduler.service /etc/systemd/system/
sudo cp config/price-scout-scheduler.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timer
sudo systemctl enable price-scout-scheduler.timer
sudo systemctl start price-scout-scheduler.timer

# Check timer status
sudo systemctl list-timers | grep price-scout

# View logs
sudo journalctl -u price-scout-scheduler -f
```

### Configuration

Edit the service files before deployment:

1. **User/Group**: Change `User=sergey` to your username
2. **WorkingDirectory**: Update path to your project directory
3. **DATABASE_URL**: Update PostgreSQL connection string
4. **ExecStart**: Update path to compiled binaries

### Prerequisites

1. **Compiled Binaries**:
   ```bash
   cargo build --release
   ```

2. **Database Access**:
   - PostgreSQL server running on 192.168.0.10:5432
   - Database `price_scout` created
   - Migrations applied

3. **Python Environment**:
   - Python 3.10+ with dependencies
   - Virtual environment activated (if using venv)

### Monitoring

```bash
# Worker status
sudo systemctl status price-scout-worker

# Scheduler timer status
sudo systemctl status price-scout-scheduler.timer

# View recent jobs
psql postgresql://postgres@192.168.0.10:5432/price_scout \
  -c "SELECT id, product_id, store_id, status, scheduled_at FROM scraping_jobs ORDER BY id DESC LIMIT 20;"

# Check job queue stats
curl http://localhost:3000/api/queue/stats
```

### Troubleshooting

**Service fails to start:**
- Check binary path: `ls -la target/release/price-scout-worker`
- Check database connection: `psql $DATABASE_URL -c "SELECT 1"`
- Check logs: `sudo journalctl -u price-scout-worker -n 50`

**No jobs being processed:**
- Check worker is running: `sudo systemctl status price-scout-worker`
- Check pending jobs: Query `scraping_jobs` table
- Check worker logs for errors

**Jobs failing:**
- Check Python environment is accessible
- Check Python dependencies installed
- Check `test_scrapers.py` runs manually
- Check rate limiting (HTTP 429) in logs

### Rate Limiting Strategy

- **Worker poll_interval**: 600 seconds (10 minutes)
- **Per-store delays**: 1-5 seconds (configured in StoreConfig)
- **Batch size**: 10 jobs at a time
- **Total cycle time**: ~10-15 minutes for all products across all stores

This ensures we don't overwhelm stores with requests and avoid rate limiting.
