# 📧 Email и Telegram Уведомления - Инструкция по настройке

## Обзор

Система поддерживает автоматические уведомления через:
- **Email (SendGrid)**: Уведомления об оплате и истечении подписки
- **Telegram Bot**: Уведомления о support tickets для админов

---

## 1. 📧 Настройка Email уведомлений (SendGrid)

### Шаг 1: Создание аккаунта SendGrid

1. Зарегистрируйтесь на https://sendgrid.com
2. Подтвердите ваш email
3. Перейдите в раздел **Settings → API Keys**

### Шаг 2: Создание API ключа

1. Нажмите **Create API Key**
2. Название: `AnonVPN-Notifications`
3. Права доступа: **Full Access** (или минимум **Mail Send**)
4. Нажмите **Create & View**
5. **ВАЖНО**: Скопируйте ключ сейчас - он больше не будет показан!

### Шаг 3: Верификация отправителя

1. Перейдите в **Settings → Sender Authentication**
2. Выберите **Single Sender Verification** (бесплатно)
3. Заполните форму:
   - From Name: `AnonVPN`
   - From Email Address: ваш email (например, `noreply@yourdomain.com`)
4. Проверьте email и подтвердите

### Шаг 4: Настройка в приложении

Добавьте в `/app/backend/.env`:

```bash
SENDGRID_API_KEY="ваш_api_ключ_здесь"
SENDER_EMAIL="noreply@yourdomain.com"
```

### Шаг 5: Перезапуск сервера

```bash
sudo supervisorctl restart backend
sudo supervisorctl restart celery
```

### Тест Email уведомлений

```bash
# Проверка через Python
python3 -c "
from backend.email_service import email_service
result = email_service.send_payment_confirmation(
    'test@example.com',
    {
        'amount': 99.99,
        'currency': 'USD',
        'plan_name': 'Pro Plan',
        'payment_id': 'test-123',
        'crypto_currency': 'BTC',
        'crypto_amount': 0.002,
        'expires_at': '2025-12-31'
    }
)
print('Email sent:', result)
"
```

---

## 2. 🤖 Настройка Telegram уведомлений

### Шаг 1: Создание Telegram бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Имя бота: `AnonVPN Support Bot`
   - Username: `anonvpn_support_bot` (должен заканчиваться на `bot`)
4. **Сохраните токен** который вам дал BotFather

### Шаг 2: Получение Chat ID

Есть два способа:

#### Способ A: Через userinfobot
1. Найдите [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте `/start`
3. Скопируйте ваш **Chat ID** (число, например: `123456789`)

#### Способ B: Через ваш бот
1. Отправьте любое сообщение вашему боту
2. Откройте в браузере:
   ```
   https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates
   ```
3. Найдите `"chat":{"id":123456789}` в ответе

### Шаг 3: Настройка в приложении

Добавьте в `/app/backend/.env`:

```bash
TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
```

Перезапустите backend:
```bash
sudo supervisorctl restart backend
```

### Шаг 4: Настройка Chat IDs для админов

Используйте API endpoint для настройки:

```bash
curl -X POST "http://localhost:8001/api/admin/telegram/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "admin_chat_ids": ["123456789", "987654321"],
    "enabled": true,
    "notify_new_tickets": true,
    "notify_ticket_replies": true,
    "notify_ticket_status_change": true
  }'
```

### Шаг 5: Тест Telegram уведомлений

```bash
# Тест подключения
curl -X POST "http://localhost:8001/api/admin/telegram/test?chat_id=ВАШ_CHAT_ID"
```

Вы должны получить тестовое сообщение в Telegram!

---

## 3. 🔔 Типы уведомлений

### Email уведомления

| Событие | Когда отправляется | Функция |
|---------|-------------------|---------|
| **Подтверждение оплаты** | Когда payment status = "finished" или "confirmed" | `send_payment_confirmation()` |
| **Истечение за 7 дней** | Ежедневно в 9:00 UTC (Celery) | `send_subscription_expiry_warning()` |
| **Истечение за 3 дня** | Ежедневно в 9:00 UTC (Celery) | `send_subscription_expiry_warning()` |
| **Истечение за 1 день** | Ежедневно в 9:00 UTC (Celery) | `send_subscription_expiry_warning()` |
| **Подписка истекла** | Когда подписка истекает (Celery) | `send_subscription_expired()` |

### Telegram уведомления

| Событие | Когда отправляется | Функция |
|---------|-------------------|---------|
| **Новый тикет** | При создании support ticket | `notify_new_support_ticket()` |
| **Ответ на тикет** | При добавлении ответа | `notify_ticket_reply()` |
| **Изменение статуса** | При изменении статуса тикета | `notify_ticket_status_change()` |

---

## 4. ⚙️ Celery для фоновых задач

### Запуск Celery

Celery уже настроен и должен быть запущен:

```bash
# Проверка статуса
sudo supervisorctl status celery

# Перезапуск при необходимости
sudo supervisorctl restart celery
```

### Расписание задач

- **Проверка pending payments**: Каждые 2 минуты
- **Проверка истекающих подписок**: Ежедневно в 9:00 UTC

### Логи Celery

```bash
# Просмотр логов
tail -f /var/log/celery_worker.log

# Или supervisor логи
tail -f /var/log/supervisor/celery.err.log
```

---

## 5. 🧪 Тестирование

### Тест всей цепочки Email

1. Создайте тестовую оплату через Dashboard
2. Дождитесь подтверждения (или используйте webhook simulator)
3. Проверьте email ящик

### Тест Support Ticket

1. Создайте support ticket через API или UI:
```bash
curl -X POST "http://localhost:8001/api/support/tickets" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-id",
    "subject": "Test Ticket",
    "description": "This is a test support ticket",
    "priority": "high",
    "category": "technical"
  }'
```

2. Проверьте Telegram - должно прийти уведомление

---

## 6. 🔍 Отладка

### Email не приходят

1. **Проверьте API ключ**:
```bash
grep SENDGRID_API_KEY /app/backend/.env
```

2. **Проверьте логи backend**:
```bash
tail -100 /var/log/supervisor/backend.err.log | grep -i email
```

3. **Проверьте SendGrid Dashboard**:
   - Перейдите на https://app.sendgrid.com/email_activity
   - Посмотрите статус отправленных писем

4. **Email могут попасть в SPAM** - проверьте spam папку

### Telegram уведомления не работают

1. **Проверьте бот токен**:
```bash
# Проверка через API Telegram
curl "https://api.telegram.org/bot<ВАШ_ТОКЕН>/getMe"
```

2. **Проверьте Chat ID**:
```bash
# Должен вернуть success
curl "http://localhost:8001/api/admin/telegram/settings"
```

3. **Проверьте логи**:
```bash
tail -100 /var/log/supervisor/backend.err.log | grep -i telegram
```

4. **Убедитесь что бот запущен** (`/start` команда отправлена боту)

---

## 7. 📝 Важные замечания

### SendGrid
- **Free tier**: 100 emails/day бесплатно
- **Верификация домена**: Для production рекомендуется верифицировать домен
- **IP Reputation**: Не отправляйте spam, иначе IP будет заблокирован

### Telegram
- **Rate Limits**: Максимум 30 сообщений/секунду для группы
- **Бот должен быть добавлен**: Если отправляете в группу, добавьте бота в группу
- **Long Polling vs Webhooks**: Текущая реализация без webhooks (проще для начала)

### Celery
- **Redis должен работать**: `sudo systemctl status redis`
- **Проверка задач**: Используйте Celery Flower для мониторинга
- **Timezone**: Все задачи в UTC

---

## 8. 🚀 Production Checklist

- [ ] SendGrid API ключ настроен
- [ ] Email отправителя верифицирован в SendGrid
- [ ] Telegram бот токен настроен
- [ ] Admin Chat IDs добавлены
- [ ] Celery запущен и работает
- [ ] Redis работает
- [ ] Проверены email уведомления (тест)
- [ ] Проверены Telegram уведомления (тест)
- [ ] Логи проверены на ошибки
- [ ] Email не попадают в SPAM

---

## 9. 🆘 Поддержка

Если возникли проблемы:

1. Проверьте логи: `/var/log/supervisor/backend.err.log`
2. Проверьте статус сервисов: `sudo supervisorctl status`
3. Проверьте .env файл: `cat /app/backend/.env`
4. Проверьте документацию:
   - SendGrid: https://docs.sendgrid.com
   - Telegram Bot API: https://core.telegram.org/bots/api

---

**Последнее обновление**: January 2025
**Версия**: 1.0
