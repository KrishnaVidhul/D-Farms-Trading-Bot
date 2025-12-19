#!/usr/bin/env python3
import os
import sys
import logging
import subprocess
import requests
from datetime import datetime

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SNIPER_DIR = os.path.expanduser("~/arm_sniper")
SUCCESS_FLAG = os.path.join(SNIPER_DIR, ".provisioned")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(SNIPER_DIR, "sniper.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ARMSniper")

def send_telegram(message):
    """Send Telegram alert"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.warning("Telegram not configured")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Telegram failed: {e}")

def check_if_already_provisioned():
    """Check if we already successfully provisioned an instance"""
    if os.path.exists(SUCCESS_FLAG):
        logger.info("Instance already provisioned. Sniper inactive.")
        return True
    return False

def check_arm_availability():
    """
    Check if Ampere A1 capacity is available
    Returns: True if available, False otherwise
    """
    try:
        # Check if OCI is configured
        oci_config = os.path.expanduser("~/.oci/config")
        if not os.path.exists(oci_config):
            logger.warning("OCI credentials not configured")
            return False
        
        import oci
        
        config = oci.config.from_file()
        compute_client = oci.core.ComputeClient(config)
        
        # Get availability domain
        identity_client = oci.identity.IdentityClient(config)
        ads = identity_client.list_availability_domains(config['tenancy']).data
        
        if not ads:
            logger.error("No availability domains found")
            return False
        
        ad_name = ads[0].name
        
        # Try to get shape availability
        shape_name = "VM.Standard.A1.Flex"
        
        try:
            # This will fail with capacity error if not available
            # We're just testing, not actually creating
            logger.info(f"Checking {shape_name} availability in {ad_name}")
            
            # Query compute capacity
            capacity_report = compute_client.list_compute_capacity_reservations(
                compartment_id=config['tenancy']
            )
            
            # If we get here without error, capacity might be available
            # The real test is trying to launch
            logger.info("Capacity check passed - attempting provision")
            return True
            
        except oci.exceptions.ServiceError as e:
            if "Out of host capacity" in str(e):
                logger.info("No capacity available")
                return False
            else:
                logger.error(f"Service error: {e}")
                return False
                
    except ImportError:
        logger.error("OCI SDK not installed")
        return False
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        return False

def provision_instance():
    """
    Provision Ampere A1 instance using Terraform
    """
    try:
        terraform_dir = os.path.join(SNIPER_DIR, "terraform")
        
        if not os.path.exists(terraform_dir):
            logger.error("Terraform directory not found")
            return False
            
        # Optimization: Only init if needed
        if not os.path.exists(os.path.join(terraform_dir, ".terraform")):
            logger.info("Initializing Terraform...")
            subprocess.run(["terraform", "init"], cwd=terraform_dir, capture_output=True)
        
        logger.info("🚀 Starting Aggressive Provisioning Sequence...")
        
        # Aggressive Retry Loop (Try 5 times immediately)
        for i in range(1, 6):
            logger.info(f"Attempt {i}/5: Applying Terraform...")
            
            result = subprocess.run(
                ["terraform", "apply", "-auto-approve"],
                cwd=terraform_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info("✅ Terraform provisioning successful!")
                # Mark as provisioned
                with open(SUCCESS_FLAG, 'w') as f:
                    f.write(datetime.now().isoformat())
                return True
            
            # Check error
            err = result.stderr
            if "Out of host capacity" in err or "500" in err:
                logger.warning(f"Attempt {i} failed: Capacity busy/gone. Retrying immediately...")
            else:
                logger.error(f"Terraform error: {err[:200]}...")
                
            # Tiny sleep between hammers
            import time
            time.sleep(2)
            
        return False

    except Exception as e:
        logger.error(f"Provisioning error: {e}")
        return False

def main():
    """
    Continuous Sniper Logic (Runs for ~280s to fit inside 5m cron)
    """
    logger.info("🔫 ARM Sniper 2.0 (Continuous Mode) starting...")
    
    start_time = datetime.now()
    
    # 5 Minute Cron = 300s. We run for 280s then exit to let next cron take over.
    MAX_RUNTIME_SEC = 280 
    
    while (datetime.now() - start_time).total_seconds() < MAX_RUNTIME_SEC:
        
        # 1. Check Success Flag
        if check_if_already_provisioned():
            sys.exit(0)
            
        # 2. Check Availability
        if check_arm_availability():
            logger.info("🎯 CAPACITY DETECTED! GO GO GO!")
            
            # Send alert (only once per detection to avoid spam, maybe?)
            # send_telegram("🎯 *Capacity Detected!* Auto-deploying...")
            
            if provision_instance():
                message = """
🎉 *ARM Instance Provisioned!*
✅ Shape: VM.Standard.A1.Flex (4 CPU / 24 GB)
✅ Cost: FREE
"""
                send_telegram(message)
                sys.exit(0)
        
        # 3. Sleep briefly
        import time
        time.sleep(10) # Check every 10 seconds

    logger.info("Sniper cycle finished. Handing over to next cron.")

if __name__ == "__main__":
    main()
