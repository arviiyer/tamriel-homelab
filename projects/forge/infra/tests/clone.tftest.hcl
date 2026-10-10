mock_provider "proxmox" {}

variables {
  endpoint            = "https://pve-01.example.com:8006/"
  ssh_public_key_file = "tests/operator.pub"
  vms = {
    apps-01 = {
      id    = 201, node = "pve-01", template_id = 9000, template_node = "pve-01"
      cores = 4, memory = 8192, protected = true
    }
    test-01 = {
      id    = 301, node = "pve-01", template_id = 9001, template_node = "pve-01"
      cores = 2, memory = 4096, protected = false
    }
  }
}

run "independent_vm_settings" {
  command = plan
  assert {
    condition = (
      proxmox_virtual_environment_vm.vm["apps-01"].cpu[0].cores == 4 &&
      proxmox_virtual_environment_vm.vm["test-01"].cpu[0].cores == 2 &&
      proxmox_virtual_environment_vm.vm["apps-01"].clone[0].vm_id == 9000 &&
      proxmox_virtual_environment_vm.vm["test-01"].clone[0].vm_id == 9001
    )
    error_message = "Each VM must retain its own resources and template."
  }
  assert {
    condition = (
      proxmox_virtual_environment_vm.vm["apps-01"].protection &&
      !proxmox_virtual_environment_vm.vm["test-01"].protection
    )
    error_message = "Protection must apply to the selected VM."
  }
  assert {
    condition = (
      proxmox_virtual_environment_vm.vm["test-01"].clone[0].full &&
      proxmox_virtual_environment_vm.vm["test-01"].initialization[0].ip_config[0].ipv4[0].address == "dhcp"
    )
    error_message = "Clones must have independent disks and DHCP configuration."
  }
}
