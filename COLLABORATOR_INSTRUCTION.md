# Инструкция: Добавление коллаборатора в репозиторий GitHub

## Для владельца репозитория (MatinIvan)

### Способ 1: Добавить как Collaborator (Рекомендуется)

Этот способ даёт полный доступ к репозиторию (push, pull, merge).

**Шаги:**

1. Открой репозиторий: https://github.com/MatinIvan/Repo12

2. Перейди в **Settings** (шестерёнка справа вверху)

3. В левом меню выбери **Collaborators** (или "Collaborators and teams")

4. Нажми кнопку **Add people**

5. Введи GitHub username коллеги или его email

6. Выбери уровень доступа:
   - **Read** - только чтение
   - **Write** - чтение + push (нужен этот!)
   - **Admin** - полный контроль

7. Нажми **Add [username] to this repository**

8. Коллега получит приглашение на email и в GitHub notifications

---

### Способ 2: Deploy Key (для CI/CD или автоматизации)

Используется для автоматического доступа с сервера.

**Шаги:**

1. Коллега генерирует SSH-ключ (если ещё нет):
   ```bash
   ssh-keygen -t ed25519 -C "price-scout-deploy"
   ```

2. Коллега отправляет **публичный** ключ владельцу:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

3. Владелец открывает: **Settings -> Deploy keys -> Add deploy key**

4. Вставляет публичный ключ, даёт название

5. Ставит галочку **Allow write access** (для push)

6. Нажимает **Add key**

---

## Для коллеги (после приглашения)

### После добавления как Collaborator:

1. Проверь email или GitHub notifications - там будет приглашение

2. Прими приглашение (Accept invitation)

3. Настрой SSH (если ещё не настроен):
   ```bash
   # Проверить есть ли ключ
   ls ~/.ssh/id_*.pub

   # Если нет - создать
   ssh-keygen -t ed25519 -C "your_email@example.com"

   # Скопировать публичный ключ
   cat ~/.ssh/id_ed25519.pub
   ```

4. Добавь SSH-ключ в свой GitHub аккаунт:
   - GitHub -> Settings -> SSH and GPG keys -> New SSH key
   - Вставь содержимое публичного ключа
   - Дай название (например: "Work laptop")
   - Save

5. Проверь подключение:
   ```bash
   ssh -T git@github.com
   # Должно ответить: "Hi username! You've successfully authenticated..."
   ```

6. Клонируй или обнови remote:
   ```bash
   # Клонировать
   git clone git@github.com:MatinIvan/Repo12.git

   # Или обновить существующий remote на SSH
   git remote set-url origin git@github.com:MatinIvan/Repo12.git
   ```

7. Теперь можно пушить:
   ```bash
   git push -u origin feature/price-scout-docs
   ```

---

## Проверка доступа

```bash
# Проверить remote URL
git remote -v

# Должно показать:
# origin  git@github.com:MatinIvan/Repo12.git (fetch)
# origin  git@github.com:MatinIvan/Repo12.git (push)

# Тест push
git push --dry-run origin feature/price-scout-docs
```

---

## Troubleshooting

### Ошибка "Permission denied (publickey)"

```bash
# Проверить SSH agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Проверить подключение
ssh -vT git@github.com
```

### Ошибка "Repository not found"

- Проверь, что приглашение принято
- Проверь URL репозитория
- Убедись, что используешь SSH URL (git@github.com:...), а не HTTPS

### Ошибка "Could not read from remote repository"

```bash
# Проверить права на ключ
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```
