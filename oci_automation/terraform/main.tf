terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
  }
}

provider "oci" {
  config_file_profile = "DEFAULT"
}

# Get availability domains
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

# Get latest Ubuntu image
data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# Create Ampere A1 instance
resource "oci_core_instance" "ampere_a1" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = "Trading-Bot-ARM"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  create_vnic_details {
    subnet_id        = var.subnet_id
    assign_public_ip = true
    display_name     = "trading-bot-arm-vnic"
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu.images[0].id
    boot_volume_size_in_gbs = 100
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
      telegram_token = var.telegram_token
      chat_id        = var.chat_id
    }))
  }

  preserve_boot_volume = false

  lifecycle {
    ignore_changes = [
      source_details[0].source_id
    ]
  }
}

output "instance_public_ip" {
  value = oci_core_instance.ampere_a1.public_ip
}

output "instance_id" {
  value = oci_core_instance.ampere_a1.id
}
