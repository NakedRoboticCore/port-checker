import requests
import apprise
import os
from time import localtime, sleep, strftime, time

__version__ = "0.0.1"
domain = os.getenv("DOMAIN", "")
port = int(os.getenv("PORT", "443"))
apprise_url = os.getenv("APPRISE_URL", "")
check_interval = int(os.getenv("CHECK_INTERVAL", "60"))
retry_delay = int(os.getenv("RETRY_DELAY", "5"))

if apprise_url:
    notifier = apprise.Apprise()
    notifier.add(apprise_url)

def log(message):
    t = time()
    t_str = strftime("%Y-%m-%d %H:%M:%S", localtime(t))
    print(f"[{t_str}] {message}")

def notify(message, title="Port Checker", notify_type=apprise.NotifyType.INFO):
    notifier.notify(
        body=message,
        title=title,
        notify_type=notify_type
    )

def get_public_ip():
    """Obtiene la IP pública del host para el log"""
    try:
        response = requests.get("https://api.ipify.org?format=text", timeout=5)
        return response.text.strip()
    except Exception as e:
        log(f"❌ Error obtaining public IP address: {e}")
        return "Unknown"
    
def call_port_api():
    """Llamada aislada a la API externa"""
    url = f"https://portchecker.io/api/{domain}/{port}"
    try:
        response = requests.get(url, timeout=10)
        return response.text == "True"
    except Exception as e:
        log(f"❌ API error: {e}")
        notify(
            message=f"❌ API error: {e}",
            title="API Error",
            notify_type=apprise.NotifyType.ERROR
        )
        return False

def check_port_externally(previous_result):

    resolved_ip = get_public_ip() 

    is_open = call_port_api()

    if not is_open:
        log(f"🔍 Port {port} reported closed. Retrying in {retry_delay}s...")
        sleep(retry_delay)
        is_open = call_port_api()
        
    first_check = previous_result is None

    if first_check and apprise_url:
        notify(
            message=f"🚀 Initializing port-checker for port {port} at {domain} ({resolved_ip})",
            title="Port Checker Initialized"
        )

    if is_open:
        log(f"🟢 Port {port} open at {domain} ({resolved_ip})")
        if apprise_url and (previous_result is False or first_check):
            if first_check:
                log(f"📣 Port {port} is currently open at {domain} ({resolved_ip}). Sending initial notification...")
            else:
                log(f"📣 Port {port} just opened at {domain} ({resolved_ip}). Sending notification...")
            notify(
                message=f"🟢 Port {port} is open at {domain} ({resolved_ip})",
                title="Port Open"
            )
        return True
    else:
        log(f"🔴 Port {port} is not reachable at {domain} ({resolved_ip}).")
        if apprise_url and (previous_result is True or first_check):
            log(f"📣 Port {port} just closed at {domain} ({resolved_ip}). Sending notification...")
            notify(
                message=f"🔴 Port {port} is not reachable at {domain} ({resolved_ip}).",
                title="Port Closed",
                notify_type=apprise.NotifyType.WARNING
            )
        return False

if __name__ == "__main__":
    previous_result = None
    log(f"🚀 Initializing port-checker v{__version__} for port {port} at {domain} ({get_public_ip()})")
    if not domain:
        log("❌ No domain specified. Please set the DOMAIN environment variable.")
        exit(1)
    if not apprise_url:
        log("⚠️ No APPRISE_URL specified. Notifications will be disabled.")
    
    while True:
        previous_result = check_port_externally(previous_result)
        sleep(check_interval)