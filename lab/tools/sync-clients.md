# sync-clients

Синхронизация clients/ между iMac и MacBook через rsync.

## Команды

**Скачать с iMac на MacBook:**
```
rsync -avz viktorsolomonik@192.168.31.93:~/Projects/svaib/clients/ ~/Projects/svaib/clients/
```

**Отправить с MacBook на iMac:**
```
rsync -avz ~/Projects/svaib/clients/ viktorsolomonik@192.168.31.93:~/Projects/svaib/clients/
```

SSH-ключ настроен, пароль не спросит.

## Как использовать

Попробуй выполнить команду через Bash. Если ошибка "No route to host" — попроси Виктора запустить в Terminal на MacBook.
