"""
Підставляє твій AWS account ID, email і шлях до проєкту в усі конфіги.

Запуск (з кореня репозиторію):
    python configure.py <ACCOUNT_ID> <EMAIL>

Приклад:
    python configure.py 123456789012 me@gmail.com
"""
import pathlib
import re
import sys

OLD_ID = "747482682250"

if len(sys.argv) != 3 or not re.fullmatch(r"\d{12}", sys.argv[1]):
    sys.exit("Використання: python configure.py <12-значний ACCOUNT_ID> <EMAIL>")

account_id, email = sys.argv[1], sys.argv[2]
root = pathlib.Path(__file__).resolve().parent
backend_dir = root / "backend" / "restaurant-backend-app"
cfg = backend_dir / ".syndicate-config-restaurant-backend-app"


def patch(path: pathlib.Path, *subs):
    text = path.read_text(encoding="utf-8")
    for pattern, repl in subs:
        text = re.sub(pattern, repl, text, flags=re.M)
    path.write_text(text, encoding="utf-8")
    print(f"  ✔ {path.relative_to(root)}")


# forward slashes work on Windows too and avoid YAML escaping problems
project_path = backend_dir.as_posix()

patch(cfg / "syndicate.yml",
      (r'^account_id:.*$', f'account_id: "{account_id}"'),
      (r'^project_path:.*$', f'project_path: "{project_path}"'),
      (r'^deploy_target_bucket:.*$', f'deploy_target_bucket: "marathon2026-restaurant-artifacts-{account_id}"'))

patch(cfg / "syndicate_aliases.yml",
      (r'^account_id:.*$', f'account_id: "{account_id}"'),
      (OLD_ID, account_id))

patch(root / "infra" / "terraform" / "backend.tf",
      (r'restaurant-terraform-state-\d+', f'restaurant-terraform-state-{account_id}'))

patch(root / "infra" / "terraform" / "variables.tf",
      (rf'default\s*=\s*"{OLD_ID}"', f'default     = "{account_id}"'),
      (r'(variable "alert_emails"[\s\S]*?default\s*=\s*)\[[^\]]*\]', rf'\1["{email}"]'))

print("\nГотово. Account ID:", account_id)
