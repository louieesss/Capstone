# Cloudflare Tunnel Setup

This project is a Flask app that must keep running on the Raspberry Pi because it uses the Pi camera, GPIO/I2C sensors, PyTorch, OpenCV, and MySQL.

## Run App And Tunnel Automatically

On the Raspberry Pi service setup, starting the app service also starts the
Cloudflare quick tunnel:

```bash
sudo systemctl start pollination-app.service
```

Check both processes:

```bash
sudo systemctl status pollination-app.service --no-pager
sudo systemctl status pollination-cloudflare-quick.service --no-pager
```

Get the generated public URL:

```bash
sudo journalctl -u pollination-cloudflare-quick.service -n 80 --no-pager
```

Open the generated `https://...trycloudflare.com` URL. For mobile camera input,
use:

```text
https://...trycloudflare.com/mobile
```

## Quick Demo Tunnel

Start the app in one terminal:

```bash
python app.py
```

Start the public HTTPS tunnel in another terminal:

```bash
./scripts/start_cloudflare_tunnel.sh
```

Open the generated `https://...trycloudflare.com` URL. For mobile camera input, use:

```text
https://...trycloudflare.com/mobile
```

## Start App And Tunnel Together

For manual terminal runs, use this instead of `python app.py`:

```bash
./scripts/run_app_with_cloudflare_tunnel.sh
```

The terminal must stay open. When the tunnel command stops, the public URL stops working.

## Installed Pi Services

This repo includes service templates:

```bash
systemd/pollination-app.service
systemd/pollination-cloudflare-quick.service
```

Useful commands after installation:

```bash
sudo systemctl status pollination-app
sudo systemctl status pollination-cloudflare-quick
sudo journalctl -u pollination-cloudflare-quick -n 80 --no-pager
sudo systemctl restart pollination-app pollination-cloudflare-quick
sudo systemctl stop pollination-cloudflare-quick pollination-app
```

## Permanent Domain Tunnel

Use this later if you want your own domain instead of a temporary `trycloudflare.com` URL:

```bash
cloudflared tunnel login
cloudflared tunnel create pollination-system
cloudflared tunnel route dns pollination-system pollination.your-domain.com
```

Then copy `cloudflare/config.example.yml` to your Cloudflare config location and replace the tunnel ID, credentials path, and hostname.

## Security Notes

Do not publish `.env` or database passwords. If credentials were already pushed to GitHub, rotate the database password.
