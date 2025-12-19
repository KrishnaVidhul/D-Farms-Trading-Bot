# OCI Automation Setup Guide

## Status: ✅ Scripts Deployed, ⏳ Awaiting Credentials

Both automation systems are deployed to your VM and scheduled via cron:
- **Cost Monitor**: Runs every hour
- **ARM Sniper**: Runs every 5 minutes

They are currently **inactive** because OCI API credentials haven't been configured yet.

## Step 1: Generate OCI API Credentials

1. Log into [Oracle Cloud Console](https://cloud.oracle.com)
2. Click your profile icon (top right) → **User Settings**
3. Scroll to **API Keys** section
4. Click **Add API Key**
5. Select **Generate API Key Pair**
6. Click **Download Private Key** (saves `oci_api_key.pem`)
7. Click **Add** - A config preview will appear
8. **Copy the entire config preview** (you'll need this)

## Step 2: Upload Credentials to VM

SSH into your VM:
```bash
ssh -i ~/.ssh/google_compute_engine ubuntu@129.153.60.198
```

Create OCI config directory:
```bash
mkdir -p ~/.oci
chmod 700 ~/.oci
```

Create config file:
```bash
nano ~/.oci/config
```

Paste the config you copied from Oracle Cloud. It should look like:
```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaa...
fingerprint=aa:bb:cc:dd:ee:ff...
tenancy=ocid1.tenancy.oc1..aaaaaaaa...
region=ca-toronto-1
key_file=~/.oci/oci_api_key.pem
```

Save and exit (Ctrl+X, Y, Enter).

## Step 3: Upload Private Key

On your **local Mac**, upload the private key you downloaded:
```bash
scp -i ~/.ssh/google_compute_engine ~/Downloads/oci_api_key.pem ubuntu@129.153.60.198:~/.oci/
```

Set permissions on VM:
```bash
ssh -i ~/.ssh/google_compute_engine ubuntu@129.153.60.198 "chmod 600 ~/.oci/oci_api_key.pem"
```

## Step 4: Configure Terraform Variables

On the VM, create Terraform variable file:
```bash
cd ~/arm_sniper/terraform
nano terraform.tfvars
```

Add these values (get OCIDs from Oracle Cloud Console):
```hcl
tenancy_ocid      = "ocid1.tenancy.oc1..aaaaaaaa..."  # From ~/.oci/config
compartment_ocid  = "ocid1.compartment.oc1..aaaaaaaa..."  # Your compartment OCID
subnet_id         = "ocid1.subnet.oc1.ca-toronto-1.aaaaaaaa..."  # Your subnet OCID
telegram_token    = "YOUR_TELEGRAM_BOT_TOKEN"
chat_id           = "YOUR_TELEGRAM_CHAT_ID"
```

**How to find OCIDs:**
- **Compartment OCID**: Console → Identity → Compartments → Click your compartment → Copy OCID
- **Subnet OCID**: Console → Networking → Virtual Cloud Networks → Click your VCN → Subnets → Copy OCID

Save and exit.

## Step 5: Test the Systems

### Test Cost Monitor
```bash
python3 ~/oci_monitor/cost_tracker.py
```

Expected output: `Database initialized` and cost data logged.

### Test ARM Sniper
```bash
python3 ~/arm_sniper/arm_sniper.py
```

Expected output: `ARM Sniper starting...` and availability check result.

## Step 6: Monitor Logs

Check if cron jobs are running:
```bash
# Cost monitor log
tail -f ~/oci_monitor/cron.log

# ARM sniper log
tail -f ~/arm_sniper/cron.log
```

## What Happens Next

### Cost Monitor
- Runs every hour automatically
- Stores cost data in `~/oci_monitor/costs.db`
- Sends daily Telegram report at 8 AM UTC with:
  - Total cost (24h)
  - Average per hour
  - Peak hour cost

### ARM Sniper
- Checks Ampere A1 availability every 5 minutes
- When capacity is detected:
  1. Sends Telegram alert: "Capacity Detected!"
  2. Runs Terraform to provision instance
  3. Sends success/failure alert
  4. Auto-deactivates after successful provision

## Troubleshooting

### "OCI credentials not configured"
- Verify `~/.oci/config` exists and has correct format
- Verify `~/.oci/oci_api_key.pem` exists
- Check permissions: `ls -la ~/.oci/`

### "Terraform errors"
- Verify `terraform.tfvars` has all required variables
- Run `cd ~/arm_sniper/terraform && terraform init` manually
- Check Terraform logs

### "No Telegram alerts"
- Verify `TELEGRAM_TOKEN` and `CHAT_ID` in environment
- Test: `echo $TELEGRAM_TOKEN` (should show your token)

## Manual Commands

Force cost check now:
```bash
python3 ~/oci_monitor/cost_tracker.py
```

Force ARM availability check now:
```bash
python3 ~/arm_sniper/arm_sniper.py
```

View cost database:
```bash
sqlite3 ~/oci_monitor/costs.db "SELECT * FROM hourly_costs ORDER BY timestamp DESC LIMIT 10;"
```

Stop sniper (if needed):
```bash
crontab -l | grep -v arm_sniper | crontab -
```

## Files Location

```
~/oci_monitor/
├── cost_tracker.py      # Main script
├── costs.db            # SQLite database
├── cost_tracker.log    # Application log
└── cron.log           # Cron execution log

~/arm_sniper/
├── arm_sniper.py       # Main script
├── sniper.log         # Application log
├── cron.log          # Cron execution log
├── .provisioned      # Flag file (created after success)
└── terraform/
    ├── main.tf
    ├── variables.tf
    ├── terraform.tfvars  # Your secrets (create this)
    └── cloud-init.yaml
```

## Security Notes

- All credentials are stored with restricted permissions (600/700)
- Terraform state contains sensitive data - keep VM secure
- The sniper auto-stops after provisioning to prevent duplicate instances
- Cost data is stored locally, not transmitted anywhere except Telegram reports
