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
  # Credentials come from PROXMOX_VE_API_TOKEN.
}

resource "proxmox_virtual_environment_vm" "vm" {
  for_each        = var.vms
  name            = each.key
  node_name       = each.value.node
  vm_id           = each.value.id
  protection      = each.value.protected
  stop_on_destroy = true

  clone {
    vm_id     = each.value.template_id
    node_name = each.value.template_node
    full      = true
  }
  cpu {
    cores = each.value.cores
    type  = "host"
  }
  memory {
    dedicated = each.value.memory
  }
  agent {
    enabled = true
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
  lifecycle {
    # Power changes happen through the Proxmox API, not a later clone request.
    ignore_changes = [started]
  }
}
