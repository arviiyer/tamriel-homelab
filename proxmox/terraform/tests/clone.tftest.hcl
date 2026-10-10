mock_provider "proxmox" {}

variables {
  endpoint            = "https://pve-01.example.com:8006/"
  node                = "pve-01"
  template_id         = 9000
  vm_id               = 301
  ssh_public_key_file = "tests/operator.pub"
}

run "clone_plan" {
  command = plan
  assert {
    condition     = proxmox_virtual_environment_vm.example.clone[0].full
    error_message = "The example must make an independent full clone."
  }
  assert {
    condition     = proxmox_virtual_environment_vm.example.initialization[0].ip_config[0].ipv4[0].address == "dhcp"
    error_message = "The clone must obtain its own address."
  }
  assert {
    condition     = proxmox_virtual_environment_vm.example.stop_on_destroy
    error_message = "The guest must be stopped before deletion."
  }
}

run "reject_plain_http" {
  command = plan
  variables {
    endpoint = "http://pve-01.example.com:8006/"
  }
  expect_failures = [var.endpoint]
}

run "reject_invalid_id" {
  command = plan
  variables {
    vm_id = 1
  }
  expect_failures = [var.vm_id]
}
