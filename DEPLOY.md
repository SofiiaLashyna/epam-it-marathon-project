# Quick Deploy (Windows PowerShell)

A condensed, copy-paste version of the deployment steps from [README.md](README.md), tested on Windows 11.
Run every command from the repository root unless a step says otherwise.

> You do not need to create Lambda functions in the AWS console: `syndicate deploy` creates `api-handler`, `reports-handler` and `report-sender` for you.

## 0. Tools (once)

```powershell
winget install -e --id Amazon.AWSCLI
winget install -e --id Hashicorp.Terraform
winget install -e --id Microsoft.DotNet.SDK.10
winget install -e --id Python.Python.3.11      # Syndicate needs 3.10–3.11
winget install -e --id OpenJS.NodeJS.LTS       # Angular 22 needs Node ^22.22.3 or ^24.15.0
```

Open a **new** PowerShell window, then check:

```powershell
aws --version; terraform -version; dotnet --version; py -3.11 --version; node --version
```

AWS access: **IAM → Users → Create user** → attach `AdministratorAccess` → **Security credentials → Create access key (CLI)**.

```powershell
aws configure                  # region: us-west-2, output: json
aws sts get-caller-identity    # prints your Account
```

The whole project is configured for **us-west-2**. Use that region.

## 1. Configure the project for your account

```powershell
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
py -3.11 configure.py $ACCOUNT_ID you@example.com
```

Updates `syndicate.yml`, `syndicate_aliases.yml` (incl. `project_path`), `backend.tf` and `variables.tf`.
Re-run it if you move the project folder. Use a path without spaces or non-Latin characters.

## 2. Terraform

```powershell
aws s3api create-bucket --bucket restaurant-terraform-state-$ACCOUNT_ID --region us-west-2 --create-bucket-configuration LocationConstraint=us-west-2
aws s3api put-bucket-versioning --bucket restaurant-terraform-state-$ACCOUNT_ID --versioning-configuration Status=Enabled

cd infra/terraform
terraform init
terraform apply -auto-approve    # CloudFront takes 5–15 min
cd ../..
```

Confirm the **AWS Notification – Subscription Confirmation** email.

## 3. Backend (Syndicate)

```powershell
cd backend/restaurant-backend-app
dotnet test Tests

py -3.11 -m venv syndicate_venv
.\syndicate_venv\Scripts\Activate.ps1           # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install aws-syndicate

$env:SDCT_CONF = (Resolve-Path ".\.syndicate-config-restaurant-backend-app").Path
syndicate create-deploy-target-bucket
syndicate build
syndicate deploy --deploy_name dev               # "Processing api_gateway resources" is slow (5–15 min), this is normal
cd ../..
```

For later code changes: `syndicate build` then `syndicate update`.

## 4. Demo data

With the venv still active (it has `boto3`):

```powershell
python scripts\seed_demo_data.py
```

See [Demo data](README.md#demo-data) in the README.

## 5. Frontend

```powershell
$API_ID = aws apigateway get-rest-apis --region us-west-2 --query "items[?name=='restaurant-backend-api'].id | [0]" --output text
$env:BACKEND_URL = "https://$API_ID.execute-api.us-west-2.amazonaws.com/develop"

cd frontend/restaurant-frontend-app
npm ci
npm run build
aws s3 sync dist/restaurant-frontend-app/browser s3://restaurant-frontend-$ACCOUNT_ID/ --delete
cd ../../infra/terraform
terraform output cloudfront_distribution_domain_name     # your site: https://<this value>
cd ../..
```

CloudFront caches pages: after a re-deploy, hard-refresh with **Ctrl+F5**.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'boto3'` | The Syndicate venv is not active in this window: run `.\backend\restaurant-backend-app\syndicate_venv\Scripts\Activate.ps1` |
| `syndicate update` ends with `Connection was closed ... /stages/develop` | Network hiccup at the last step. Lambda code is already updated; republish the stage: `aws apigateway create-deployment --rest-api-id $API_ID --stage-name develop --region us-west-2` |
| `$API_ID` is `None` | The backend deploy has not finished or failed. Check the `syndicate deploy` output |
| `npm run build` says `BACKEND_URL is not set` | Set `$env:BACKEND_URL` in the same window before building |
| GitHub Actions fail with `Credentials could not be loaded` | The workflows in `.github/workflows` expect repo secrets. For manual deploys, disable them: **Settings → Actions → General → Disable actions** |

## Clean up

When you no longer need the environment, follow [Clean up all resources](README.md#clean-up-all-resources) in the README.
