# Terragrunt Ansible Hook

The script has been tested in an environment where ansible-playbook is executed as a Terragrunt hook (before_hook and after_hook).
Why is it worth using Ansible together with Terragrunt and Terraform? Ansible is very good at managing service and container configuration files, as well as creating directory structures. Unfortunately, Terragrunt does not provide hook logic that would be able to skip script execution when there are “No changes”. This script is one of the options that can be used in such a case.

The main need addressed by this script is implementing logic that decides whether Ansible needs to be executed or not. Even though Ansible itself can determine whether the set of tasks defined in a playbook should be executed, this is a time-consuming operation. The script allows this need to be identified earlier. It is based on the provided plan file — it reads it and decides whether to run ansible-playbook, and if so, on which hosts. This allows for significant optimization of automation and CI/CD execution time.

## Scenarios

### Creating new VM machines

After creating a VM, we introduce a custom Docker daemon configuration to allow Terraform to deploy containers. We can also immediately configure a service of a given type, e.g. an NFS server.

### Creating Docker containers

Before a container is created, it often requires a directory for persistent storage, and we may also generate a configuration file for the application inside the container on that storage.
For example: when running snmp-exporter, we can prepare a ready configuration with which the container will start.

## Input parameters

| Parameter                | Mandatory | Description                                   |
| ------------------------ | --------- | --------------------------------------------- |
| -i (--ansible-inventory) | Yes       | Ansible inventory filename                    |
| -p (--playbook)          | Yes       | Ansible playbook filename                     |
| -t (--tgplan)            | YES       | Terragrunt plan file in JSON format           |
| -f (--var-file)          | No        | Additional variables required by the playbook |

## Examples

### Playbook without additional variables

```hcl
terraform {
  source = "${local.tfmodule}"
  after_hook "ansible-bootstrap" {
    commands = ["apply"]
    execute = ["python3", "${local.root.locals.rootdir}/.gitlab/hooks/ansible_hook.py",
      "-i", "${local.vmconfig.locals.ansible_inventory}",
      "-p", "${local.ansible_playbook}",
      "-t", "${local.root.locals.rootdir}/tgplans/${local.vmtype}_plan.json",
    ]
  }
}
```

### Playbook with additional variables

```hcl

# Generate ansible_vars.json file for ansible hook
generate "ansible_vars" {
  path      = "ansible_vars.json"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
{
  "docker_dirs": ${jsonencode(local.dirs_to_create)},
  "docker_files": ${jsonencode(local.files_to_create)},
  "docker_host": "${local.dockerhost}"
}
EOF
}

terraform {
  source = "${local.tfmodule}"

  before_hook "ansible-bootstrap" {
    commands = ["apply"]
    execute = ["python3", "${get_parent_terragrunt_dir()}/.gitlab/hooks/ansible_hook.py",
      "-i", "${local.ansible_inventory}",
      "-p", "${local.ansible_playbook}",
      "-t", "${get_parent_terragrunt_dir()}/tgplans/${local.dockerhost}_plan.json",
      "-f", "ansible_vars.json"
    ]
  }
}
```

### Running a container with pre-prepared configuration

1. Define a list of files based on the container configuration:

```hcl
locals {
  files_to_create = flatten([
    for container in local.params.locals.containers : [
      for volume in try(container.volumes, []) : volume.source
      if startswith(volume.source, local.source_dir_prefix) && volume.voltype == "file"
    ]
  ])
}
```

2. Generate ansible_vars.json with substituted variables:

```hcl
generate "ansible_vars" {
  path      = "ansible_vars.json"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
{
  "docker_dirs": ${jsonencode(local.dirs_to_create)},
  "docker_files": ${jsonencode(local.files_to_create)},
  "docker_host": "${local.dockerhost}"
}
EOF
}
```

3. Pass ansible_vars.json to the hook:

```hcl
terraform {
  source = "${local.tfmodule}"

  before_hook "ansible-bootstrap" {
    commands = ["apply"]
    execute = ["python3", "${get_parent_terragrunt_dir()}/.gitlab/hooks/ansible_hook.py",
      "-i", "${local.ansible_inventory}",
      "-p", "${local.ansible_playbook}",
      "-t", "${get_parent_terragrunt_dir()}/tgplans/${local.dockerhost}_plan.json",
      "-f", "ansible_vars.json"
    ]
  }
}
```
