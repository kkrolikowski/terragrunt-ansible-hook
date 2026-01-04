import sys
import argparse
import subprocess
import json
import os

class txt:
  # Colors
  green = '\033[92m'
  bold = '\033[1m'
  red = '\033[91m'
  normal = '\033[0m'
  yellow = '\033[93m'
  blue = '\033[34m'

  # Emojis
  check = '\u2705'
  rocket = '\U0001F680'
  no_entry = '\U0001F6AB'
  ok = '\U0001F44D'



def infra_changes(tgplan: str) -> list:
  '''
  Function reads terragrunt plan output and detects if something has changed.
  It returns a list of affected hosts o an empty list.
  
  :param tgplan: File name of terragrunt plan in json format
  :type tgplan: str
  :return: List of affected hosts
  :rtype: list
  '''

  try:
    with open(tgplan) as f:
      contents = json.load(f)

    servers = []
    for ch in contents["resource_changes"]:
      if 'no-op' in ch["change"]["actions"]:
        continue
      servers.append(ch["change"]["after"]["name"])

    return servers
  except FileNotFoundError as e:
    print(f"{txt.no_entry} {txt.bold}{txt.red} [ ansible_hook ]: {e.filename} not found: {e.strerror}{txt.normal}")
    sys.exit(1)

def run_ansible(
    playbook: str, 
    inventory: str, 
    extra_vars: str | None = None, 
    affected_hosts: list[str] | None = None
  ) -> None:
  '''
  Function executes ansible-playbook command with parameters based on input data.
  It supports injecting extra variables file (must be a json file) and can limit inventory
  to a list of particular hosts

  :param playbook: Playbook file with tasks to execute
  :type playbook: str
  :param inventory: Inventory file with target hosts
  :type inventory: str
  :param extra_vars: JSON file with variables required by provided playbook
  :type extra_vars: str | None
  :param affected_hosts: List of target hosts where playbook tasks will be executed
  :type affected_hosts: list[str] | None
  '''

  cmd = ["ansible-playbook", "-i", inventory]
  
  if extra_vars:
    cmd.extend(["--extra-vars", f"@{extra_vars}"])

  if affected_hosts > 0:
    cmd.extend(["--limit", ','.join(affected_hosts)])
  cmd.append(playbook)
  print(cmd)
  subprocess.run(cmd)


parser = argparse.ArgumentParser(
  prog="ansible_hook.py",
  description="Ansible Helper",
  epilog="This script is desined to be used as terragrunt hook"
)

parser.add_argument('-i', '--ansible-inventory', help="Ansible inventory file")
parser.add_argument('-p', '--playbook', help="Plabook filename")
parser.add_argument('-t', '--tgplan', help='Terragrunt plan output in json format')
parser.add_argument('-f', '--var-file', help='Additional variables required by playbook')

args = parser.parse_args()
host = os.path.basename(args.tgplan.split("_")[0])

print(f"{txt.rocket} {txt.bold}{txt.green}[ ansible_hook ]: Looking for infrastructure changes for {host}.")

affected_hosts = infra_changes(args.tgplan)
if len(affected_hosts) == 0:
  print(f"{txt.ok} {txt.bold}{txt.green}[ ansible_hook ]: {txt.yellow}No changes for {host} was detected{txt.normal}")
  sys.exit(0)

print(f"{txt.check} {txt.bold}{txt.green}[ ansible_hook ]: Applying ansible configuration for {host}{txt.normal}")
if args.var_file:
  run_ansible(playbook=args.playbook, 
              inventory=args.ansible_inventory,
              extra_vars=args.var_file,
              affected_hosts=affected_hosts
            )
else:
  run_ansible(playbook=args.playbook, 
              inventory=args.ansible_inventory,
              affected_hosts=affected_hosts
            )
