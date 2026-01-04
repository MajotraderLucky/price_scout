#!/bin/bash
# Price Scout Migration Script
# Applies database migrations to PostgreSQL on Archbook server
# Usage: ./apply_migrations.sh [--remote|--local]

set -e  # Exit on error

# Configuration
DB_NAME="price_scout"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
MIGRATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
MODE="local"
if [ "$1" == "--remote" ]; then
    MODE="remote"
    DB_HOST="192.168.0.10"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Price Scout Database Migration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Database: ${GREEN}${DB_NAME}${NC}"
echo -e "Host: ${GREEN}${DB_HOST}:${DB_PORT}${NC}"
echo -e "User: ${GREEN}${DB_USER}${NC}"
echo -e "Mode: ${GREEN}${MODE}${NC}"
echo ""

# Check PostgreSQL connection
echo -e "${YELLOW}[1/5] Checking PostgreSQL connection...${NC}"
if ! psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Cannot connect to PostgreSQL at ${DB_HOST}:${DB_PORT}${NC}"
    echo -e "${RED}Make sure PostgreSQL is running and accessible${NC}"
    exit 1
fi
echo -e "${GREEN}[+] Connected to PostgreSQL${NC}"
echo ""

# Check if database exists
echo -e "${YELLOW}[2/5] Checking if database exists...${NC}"
if ! psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"; then
    echo -e "${YELLOW}Database ${DB_NAME} does not exist. Creating...${NC}"
    psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d postgres -c "CREATE DATABASE ${DB_NAME};"
    echo -e "${GREEN}[+] Database ${DB_NAME} created${NC}"
else
    echo -e "${GREEN}[+] Database ${DB_NAME} already exists${NC}"
fi
echo ""

# Apply migration 001
echo -e "${YELLOW}[3/5] Applying migration 001_initial_schema.sql...${NC}"
if psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${DB_NAME}" -f "${MIGRATION_DIR}/001_initial_schema.sql" > /dev/null 2>&1; then
    echo -e "${GREEN}[+] Migration 001 applied successfully${NC}"
else
    echo -e "${RED}ERROR: Failed to apply migration 001${NC}"
    exit 1
fi
echo ""

# Apply migration 002
echo -e "${YELLOW}[4/5] Applying migration 002_seed_stores.sql...${NC}"
if psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${DB_NAME}" -f "${MIGRATION_DIR}/002_seed_stores.sql" > /dev/null 2>&1; then
    echo -e "${GREEN}[+] Migration 002 applied successfully${NC}"
else
    echo -e "${RED}ERROR: Failed to apply migration 002${NC}"
    exit 1
fi
echo ""

# Verification
echo -e "${YELLOW}[5/5] Verifying database schema...${NC}"

# Count tables
TABLE_COUNT=$(psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';")
TABLE_COUNT=$(echo ${TABLE_COUNT} | xargs)  # Trim whitespace

# Count stores
STORE_COUNT=$(psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM stores;")
STORE_COUNT=$(echo ${STORE_COUNT} | xargs)

# Count views
VIEW_COUNT=$(psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM pg_views WHERE schemaname = 'public';")
VIEW_COUNT=$(echo ${VIEW_COUNT} | xargs)

echo -e "${GREEN}[+] Verification complete${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Migration Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Tables created: ${GREEN}${TABLE_COUNT}${NC}/7"
echo -e "Stores seeded: ${GREEN}${STORE_COUNT}${NC}/9"
echo -e "Views created: ${GREEN}${VIEW_COUNT}${NC}/2"
echo ""

# Show stores
echo -e "${BLUE}Stores in database:${NC}"
psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${DB_NAME}" -c "
SELECT
    id,
    name,
    method,
    CASE WHEN unstable THEN '[UNSTABLE]' ELSE '[STABLE]' END AS status
FROM stores
ORDER BY unstable, id;
"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Migration completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Test connection from Rust: ${BLUE}cargo run --example test_db_connection${NC}"
echo -e "  2. Populate products table with test data"
echo -e "  3. Run scraper to populate store_prices"
echo ""
