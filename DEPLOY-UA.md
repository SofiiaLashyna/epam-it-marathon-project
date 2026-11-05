# Розгортання + Рівень 3 (групове передзамовлення)

Команди нижче для **Windows PowerShell**. Усі команди запускай з кореня проєкту (`marathon2026-main`), якщо не сказано інше.

> Lambda-функцію вручну в консолі AWS створювати **не треба**: Syndicate сам створить `api-handler`, `reports-handler` і `report-sender` під час `syndicate deploy`.

## 0. Інструменти (один раз)

Перевір, що все встановлено:

```powershell
aws --version          # AWS CLI v2
terraform -version     # >= 1.10
python --version       # 3.10 або 3.11 (на 3.12+ syndicate може не стати)
dotnet --version       # 10.x
node --version         # 22.x
```

Налаштуй доступ до AWS (IAM-користувач з AdministratorAccess → Access key для CLI):

```powershell
aws configure          # region: us-west-2, output: json
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$ACCOUNT_ID            # має вивести 12 цифр
```

## 1. Підставити свій account ID і email в конфіги

```powershell
python configure.py $ACCOUNT_ID твій_email@gmail.com
```

Скрипт оновить `syndicate.yml`, `syndicate_aliases.yml`, `backend.tf`, `variables.tf` (зокрема `project_path`).

## 2. Terraform (інфраструктура)

```powershell
aws s3api create-bucket --bucket restaurant-terraform-state-$ACCOUNT_ID --region us-west-2 --create-bucket-configuration LocationConstraint=us-west-2
aws s3api put-bucket-versioning --bucket restaurant-terraform-state-$ACCOUNT_ID --versioning-configuration Status=Enabled

cd infra/terraform
terraform init
terraform apply -auto-approve      # CloudFront створюється 5–15 хв
cd ../..
```

На пошту прийде лист від AWS SNS: натисни **Confirm subscription**.

## 3. Бекенд (Syndicate)

```powershell
cd backend/restaurant-backend-app
dotnet test Tests                  # необов'язково: перевірка, що все компілюється і тести зелені
python -m venv syndicate_venv
.\syndicate_venv\Scripts\Activate.ps1
pip install aws-syndicate
$env:SDCT_CONF = (Resolve-Path ".\.syndicate-config-restaurant-backend-app").Path
syndicate create-deploy-target-bucket
syndicate build
syndicate deploy --deploy_name dev
deactivate
cd ../..
```

Якщо `Activate.ps1` блокує політика виконання: `Set-ExecutionPolicy -Scope Process Bypass`.

## 4. Фронтенд

```powershell
$API_ID = aws apigateway get-rest-apis --region us-west-2 --query "items[?name=='restaurant-backend-api'].id | [0]" --output text
$env:BACKEND_URL = "https://$API_ID.execute-api.us-west-2.amazonaws.com/develop"

cd frontend/restaurant-frontend-app
npm ci
npm run build
aws s3 sync dist/restaurant-frontend-app/browser s3://restaurant-frontend-$ACCOUNT_ID/ --delete
cd ../../infra/terraform
terraform output cloudfront_distribution_domain_name     # ← це адреса твого сайту
cd ../..
```

Відкрий `https://<те_що_вивело>` і переконайся, що сайт працює (реєстрація або логін). **Це рівень 2.**

---

## Рівень 3: що реалізовано

Функціонал **групового передзамовлення для власника бронювання (Owner)**, за `homework-backend.md`:

| Метод | Шлях | Що робить |
|---|---|---|
| GET | `/guest/groups/{groupReservationId}/sessions` | Учасники групи, їхні страви, сума по кожному і загальна сума |
| GET | `/reservations/{reservationId}/guest-session-id` | Id власної owner-сесії (створює її, якщо ще немає) |
| POST | `/group-reservations/{groupReservationId}/submit` | Збирає страви лише з `submitted`-сесій, об'єднує однакові по `dishId`, додає в order (створює його, якщо власник ще не робив передзамовлення), ставить order → `SubmittedByCustomer`, group → `Submitted` |
| DELETE | `/guest/groups/{groupReservationId}/sessions/{guestSessionId}` | (було) видалити учасника; тепер відповідь у camelCase, як у специфікації |

Помилки: 401 без токена, 403 якщо не власник, 404 якщо reservation або group не знайдено, 400 якщо немає submitted-сесій або в них немає страв.

Змінені файли:
- `backend/.../api-handler/Services/GuestSessions/GuestSessionService.cs` (+ `IGuestSessionService.cs`): логіка
- `backend/.../api-handler/Handlers/GroupReservations/GroupPreOrderOwnerHandlers.cs`: 3 нові хендлери
- `backend/.../api-handler/Models/GroupReservation/GroupPreOrderModels.cs`: DTO
- `backend/.../api-handler/Routing/RouteRegistry.cs`: маршрути
- `backend/restaurant-backend-app/deployment_resources.json`: ендпоінти в API Gateway
- `backend/.../Repositories/GuestSessions/GuestSessionRepository.cs`: owner-сесія не займає місце гостя
- `backend/restaurant-backend-app/Tests/Services/GuestSessionServiceTests.cs`: 7 нових юніт-тестів
- Фронтенд: кнопка **Group order** на картці бронювання (`components/reservations/group-pre-order-modal/`, `services/reservation/group-pre-order.service.ts` + spec)
- `scripts/seed_demo_data.py`: демо-дані (3 локації, столики, страви, офіціанти)

### Демо-сценарій у браузері

1. `python scripts/seed_demo_data.py` (один раз, з активним `syndicate_venv`).
2. Увійди як клієнт → **Book a table** → столик на 4+ місця, гостей ≥ 2.
3. **Reservations** → картка бронювання → **Group order** → скопіюй інвайт-посилання.
4. Відкрий посилання в іншому браузері або інкогніто → введи ім'я → додай страви → **Submit**.
5. Повернись до власника → **Refresh**: видно гостя, його страви й суму → **Confirm group pre-order**.
6. Страви з'являться в передзамовленні бронювання (кнопка **Pre-order**).

### Як перевірити (PowerShell)

```powershell
$BASE = $env:BACKEND_URL
$login = Invoke-RestMethod -Method Post "$BASE/signin" -ContentType "application/json" `
  -Body '{"email":"твій_email","password":"твій_пароль"}'
$H = @{ Authorization = $login.idToken }

# id групи береться з інвайт-посилання: /guest/invites/{token} → groupReservationId
Invoke-RestMethod "$BASE/reservations/<reservationId>/guest-session-id" -Headers $H
Invoke-RestMethod "$BASE/guest/groups/<groupReservationId>/sessions" -Headers $H
Invoke-RestMethod -Method Post "$BASE/group-reservations/<groupReservationId>/submit" -Headers $H `
  -ContentType "application/json" -Body '{"reservationId":"<reservationId>"}'
```

Якщо приходить 401 з `idToken`, спробуй `$login.accessToken`.

## Прибирання після марафону (щоб AWS не брав гроші)

Дивись розділ «Clean up all resources» у `README.md`.
