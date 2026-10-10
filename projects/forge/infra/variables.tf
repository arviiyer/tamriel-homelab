variable "endpoint" {
  type = string
}
variable "bridge" {
  type    = string
  default = "vmbr0"
}
variable "datastore" {
  type    = string
  default = "local-lvm"
}
variable "ssh_public_key_file" {
  type = string
}
variable "vms" {
  type = map(object({
    id            = number
    node          = string
    template_id   = number
    template_node = string
    cores         = number
    memory        = number
    protected     = bool
  }))
  default = {}
}
