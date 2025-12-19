terraform {
  required_providers {
    oci = {
      source = "oracle/oci"
    }
  }
}

# --- Variables (You will be prompted for these) ---
variable "tenancy_ocid" {}
variable "user_ocid" {}
variable "private_key_path" {}
variable "fingerprint" {}
variable "region" {}
variable "compartment_ocid" {}
variable "ssh_public_key" {
  description = "Your local public SSH key (e.g., contents of id_rsa.pub)"
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  private_key_path = var.private_key_path
  fingerprint      = var.fingerprint
  region           = var.region
}

# --- Networking ---
resource "oci_core_vcn" "erp_vcn" {
  cidr_block     = "10.0.0.0/16"
  compartment_id = var.compartment_ocid
  display_name   = "erpnext-vcn"
}

resource "oci_core_internet_gateway" "erp_ig" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.erp_vcn.id
  display_name   = "erpnext-internet-gateway"
}

resource "oci_core_route_table" "erp_rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.erp_vcn.id
  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.erp_ig.id
  }
}

resource "oci_core_security_list" "erp_sl" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.erp_vcn.id
  display_name   = "erpnext-security-list"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  # Allow SSH (22)
  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 22
      max = 22
    }
  }

  # Allow HTTP (80)
  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }

  # Allow HTTPS (443)
  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 443
      max = 443
    }
  }
}

resource "oci_core_subnet" "erp_subnet" {
  cidr_block        = "10.0.1.0/24"
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.erp_vcn.id
  route_table_id    = oci_core_route_table.erp_rt.id
  security_list_ids = [oci_core_security_list.erp_sl.id]
  display_name      = "erpnext-public-subnet"
}

# --- Compute (The Free Tier Magic) ---

# 1. Get Availability Domains
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

# 2. Find the latest Ubuntu 22.04 Intel image
data "oci_core_images" "ubuntu_intel" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard3.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# 3. Create the Instance
resource "oci_core_instance" "erp_server" {
  # Use the first Availability Domain
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = "Trading-Bot-Main"
  shape               = "VM.Standard3.Flex"

  shape_config {
    ocpus         = 1
    memory_in_gbs = 8
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu_intel.images[0].id
    # Set boot volume size (Free tier allows up to 200GB total)
    boot_volume_size_in_gbs = 100
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.erp_subnet.id
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }
}

# --- Output ---
output "server_public_ip" {
  value = oci_core_instance.erp_server.public_ip
}
