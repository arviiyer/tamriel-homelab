variable "endpoint" {
  type        = string
  description = "HTTPS Proxmox API endpoint, including port 8006."
  validation {
    condition     = can(regex("^https://[^/]+/?$", var.endpoint))
    error_message = "Use an HTTPS endpoint such as https://pve-01.example.com:8006/."
  }
}

variable "node" {
  type        = string
  description = "Proxmox node containing the template and receiving the clone."
}

variable "template_id" {
  type = number
  validation {
    condition     = var.template_id >= 100 && floor(var.template_id) == var.template_id
    error_message = "Use the numeric ID of an existing cloud-init template."
  }
}

variable "vm_id" {
  type = number
  validation {
    condition     = var.vm_id >= 100 && floor(var.vm_id) == var.vm_id
    error_message = "Choose an unused integer VM ID of at least 100."
  }
}

variable "name" {
  type    = string
  default = "apps-01"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*[a-z0-9]$", var.name))
    error_message = "Use a lowercase hostname with letters, digits, and hyphens."
  }
}

variable "datastore" {
  type        = string
  description = "Storage for the VM disk and cloud-init drive."
  default     = "local-lvm"
}

variable "bridge" {
  type    = string
  default = "vmbr0"
}

variable "ssh_public_key_file" {
  type        = string
  description = "Path to the operator's SSH public key, never a private key."
  validation {
    condition     = can(regex("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-\\S+) ", trimspace(file(var.ssh_public_key_file))))
    error_message = "Supply an existing OpenSSH public-key file."
  }
}
