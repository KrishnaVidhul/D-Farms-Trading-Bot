variable "tenancy_ocid" {
  description = "OCI Tenancy OCID"
  type        = string
}

variable "compartment_ocid" {
  description = "OCI Compartment OCID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet OCID for the instance"
  type        = string
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "telegram_token" {
  description = "Telegram Bot Token"
  type        = string
  sensitive   = true
}

variable "chat_id" {
  description = "Telegram Chat ID"
  type        = string
  sensitive   = true
}
