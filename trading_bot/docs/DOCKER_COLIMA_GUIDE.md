# Docker & Colima Management on macOS

This guide documents how to manage your local container environment using **Colima** (Containers on Linux on Mac) and **Docker**.

## 1. Checking Status

To see if the Docker daemon and the Colima virtual machine are running:

### Check Colima (The VM)
```bash
colima status
```
- **Running**: standard output showing cpu, ram, and disk info.
- **Stopped**: `colima is not running`

### Check Docker (The Engine)
```bash
docker info
# OR simple check
docker ps
```
- if you get `Cannot connect to the Docker daemon`, the service is down.

---

## 2. Managing the Service

Since the service is configured to run **manually** (not starting on boot), use these commands:

### Start Docker
```bash
colima start
```
*Verification*: Wait for `INFO[...] done`. Then run `docker ps` to confirm.

### Stop Docker
```bash
colima stop
```
*Verification*: Run `colima status` to confirm it sees "not running".

---

## 3. Basic Docker Usage

Once `colima start` is complete, you can use standard docker commands.

### Run a Test Container
```bash
docker run --rm hello-world
```

### List Running Containers
```bash
docker ps
```

### List All Containers (including stopped)
```bash
docker ps -a
```

### Pull an Image
```bash
docker pull ubuntu
```

---

## Troubleshooting
If `docker` commands hang or fail:
1. Check `colima status`.
2. If running but unresponsive, restart:
   ```bash
   colima restart
   ```
