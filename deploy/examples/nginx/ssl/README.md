# TLS certificates

Каноничная инструкция по Nginx: [docs/deploy-examples/nginx.md](../../../../docs/deploy-examples/nginx.md).

Кладите сертификаты в подпапки, совпадающие с `WEBHOOK_HOST` и `MINIAPP_HOST`:

```text
ssl/
  webhooks.example.com/
    fullchain.pem
    privkey.pem
  app.example.com/
    fullchain.pem
    privkey.pem
```
