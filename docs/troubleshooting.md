# Troubleshooting

Common problems and solutions for Red Letters.

---

## 1. "No tokens found" or Empty Query Results

**Symptoms:**
- `redletters query "Matthew 3:2"` returns no renderings
- API returns 404 for valid references

**Cause:** Database not initialized or demo data missing.

**Solution:**

```bash
# Initialize the database with demo data
redletters init

# Verify it worked
redletters list-spans
```

If `list-spans` shows results, `query` should work for those passages.

**Still not working?** Check that the reference format is correct:
- Good: `"Matthew 3:2"`, `"John 1:1-5"`, `"Mark 1"`
- Bad: `"Matt 3:2"`, `"matthew3:2"`, `"3:2"`

---

## 2. "Port already in use" When Starting Server

**Symptoms:**
- `redletters serve` fails with "Address already in use"
- Error mentions port 8000 (or your specified port)

**Cause:** Another process is using that port.

**Solutions:**

```bash
# Option 1: Use a different port
redletters serve --port 8001

# Option 2: Find and stop the other process (macOS/Linux)
lsof -i :8000
kill <PID>

# Option 3: Find and stop the other process (Windows)
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

## 3. GUI Shows "Backend Unreachable"

**Symptoms:**
- GUI loads but shows connection error
- Dashboard shows backend as offline

**Cause:** The Python backend isn't running or isn't accessible.

**Solutions:**

1. **Start the backend:**
   ```bash
   redletters serve
   ```

2. **Check the API endpoint in GUI Settings:**
   - Default: `http://localhost:8000`
   - Ensure it matches where the backend is running

3. **Verify backend is responding:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

4. **Check for firewall issues:**
   - Some security software blocks localhost connections
   - Try temporarily disabling firewall to test

5. **If running in Docker or VM:**
   - Ensure port forwarding is configured
   - The GUI may need the host machine's IP, not `localhost`

---

## 4. Export/Quote Blocked by Gates

**Symptoms:**
- `redletters export apparatus "Mark 16" --out file.jsonl` fails
- Error: `PendingGatesError: Unacknowledged variants block export`

**Cause:** The passage contains significant textual variants that require
acknowledgement before export. This is intentional - see [Concepts: Gates](concepts.md#gates).

**Solutions:**

```bash
# Option 1: Review and acknowledge the variants
redletters gates pending "Mark 16:9"
redletters variants dossier "Mark 16:9"  # Review the evidence
redletters gates acknowledge "Mark 16:9" 0 --session my-session

# Then retry export
redletters export apparatus "Mark 16" --out file.jsonl

# Option 2: Force export (marks output as unreviewed)
redletters export apparatus "Mark 16" --out file.jsonl --force
```

Note: Using `--force` marks the output with `forced_responsibility: true`.
This is visible to anyone who reads the export.

---

## 5. Database Locked

**Symptoms:**
- Commands fail with "database is locked"
- Multiple operations hanging

**Cause:** SQLite database has a write lock from another process.

**Solutions:**

1. **Close other Red Letters processes:**
   ```bash
   # Find Python processes
   ps aux | grep redletters

   # Or on macOS
   pkill -f redletters
   ```

2. **If the lock persists (macOS/Linux):**
   ```bash
   # Find what's holding the file
   lsof ~/.greek2english/engine.db
   ```

3. **Nuclear option - copy and replace:**
   ```bash
   # Backup first!
   cp ~/.greek2english/engine.db ~/.greek2english/engine.db.backup

   # If database is corrupted, reinitialize
   rm ~/.greek2english/engine.db
   redletters init
   ```

   Note: This loses any gate acknowledgements or custom data.

---

## 6. Source Pack Installation Fails

**Symptoms:**
- `redletters sources install` hangs or errors
- "Failed to fetch" or network errors

**Cause:** Network issues, missing dependencies, or permission problems.

**Solutions:**

1. **Check network connectivity:**
   ```bash
   curl -I https://github.com
   ```

2. **If EULA required:**
   ```bash
   redletters sources install ubs-dictionary --accept-eula
   ```

3. **Check disk space and permissions:**
   ```bash
   df -h ~/.greek2english
   ls -la ~/.greek2english
   ```

4. **Try with verbose logging:**
   ```bash
   REDLETTERS_LOG_LEVEL=DEBUG redletters sources install morphgnt-sblgnt
   ```

5. **Force reinstall:**
   ```bash
   redletters sources install morphgnt-sblgnt --force
   ```

---

## 7. Wrong Data Directory

**Symptoms:**
- Data installed but not found
- Different results on different terminals

**Cause:** Multiple data roots in use, or environment variable override.

**Check your configuration:**

```bash
# See what's set
echo $REDLETTERS_DATA_ROOT

# Check default location
ls -la ~/.greek2english/

# Run with explicit data root
redletters --data-root ~/.greek2english sources status
```

**Solution:** Ensure `REDLETTERS_DATA_ROOT` is either unset (uses default)
or consistently set across terminals.

---

## 8. "Module not found" or Import Errors

**Symptoms:**
- `redletters` command not found
- Python import errors when running

**Cause:** Installation issue or wrong Python environment.

**Solutions:**

1. **Verify installation:**
   ```bash
   pip show redletters
   which redletters
   ```

2. **If using virtual environment:**
   ```bash
   # Activate your venv
   source venv/bin/activate  # or your venv path

   # Reinstall
   pip install -e .
   ```

3. **Check Python version:**
   ```bash
   python --version  # Needs 3.8+
   ```

4. **Reinstall from scratch:**
   ```bash
   pip uninstall redletters
   pip install -e .
   ```

---

## Getting More Help

### Enable Debug Logging

```bash
REDLETTERS_LOG_LEVEL=DEBUG redletters <command>
```

### Export Diagnostics

```bash
redletters diagnostics export --output diagnostics.zip
```

This creates a bundle with:
- Configuration (sanitized)
- Database schema info
- Installed pack versions
- Recent error logs

### Check Version

```bash
redletters --version
```

Ensure you're running the expected version, especially after updates.

---

## Related Documentation

- [CLI Reference](cli.md) - Full command documentation
- [Concepts](concepts.md) - Understanding gates, receipts, confidence
- [Sources & Licensing](sources-and-licensing.md) - Pack management
