terraform {
  required_version = ">= 1.7.0, < 2.0.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.116.0"
    }
  }
}

provider "proxmox" {
  endpoint = var.endpoint
  insecure = false
  # PROXMOX_VE_API_TOKEN supplies credentials outside the configuration.
}

resource "proxmox_virtual_environment_vm" "example" {
  name            = var.name
  node_name       = var.node
  vm_id           = var.vm_id
  stop_on_destroy = true

  clone {
    vm_id     = var.template_id
    node_name = var.node
    full      = true
  }

  agent {
    enabled = true
  }

  cpu {
    cores = 2
    type  = "host"
  }

  memory {
    dedicated = 4096
  }

  disk {
    datastore_id = var.datastore
    interface    = "scsi0"
    size         = 64
  }

  network_device {
    bridge = var.bridge
    model  = "virtio"
  }

  initialization {
    datastore_id = var.datastore
    user_account {
      username = "operator"
      keys     = [trimspace(file(var.ssh_public_key_file))]
    }
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }
  }
}

output "vm_id" {
  value = proxmox_virtual_environment_vm.example.vm_id
}

output "ipv4_addresses" {
  description = "Addresses reported by the guest agent, including loopback."
  value       = proxmox_virtual_environment_vm.example.ipv4_addresses
}
