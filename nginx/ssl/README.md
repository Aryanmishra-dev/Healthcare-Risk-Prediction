# SSL Certificate Setup

This directory should contain SSL certificates used by Nginx.

## Production — Let's Encrypt (Certbot)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Generate certificate (replace yourdomain.com)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certs to this directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./fullchain.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   ./privkey.pem

# Set permissions
chmod 600 privkey.pem
chmod 644 fullchain.pem
```

### Auto-Renewal

```bash
# Add to crontab
0 0 1 * * certbot renew --quiet && docker compose restart nginx
```

## Development — Self-Signed Certificate

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout privkey.pem \
  -out fullchain.pem \
  -subj "/CN=localhost"
```

## Required Files

| File             | Description                     |
|------------------|---------------------------------|
| `fullchain.pem`  | Full certificate chain          |
| `privkey.pem`    | Private key (**keep secret!**)  |

> **⚠️ Never commit `.pem` files to git.** They are already in `.gitignore`.
