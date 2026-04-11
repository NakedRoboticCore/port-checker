import requests
import apprise
import os
from time import localtime, sleep, strftime

__version__ = "0.0.2"
domain = os.getenv("DOMAIN", "")
port = int(os.getenv("PORT", "443"))
apprise_url = os.getenv("APPRISE_URL", "")
check_interval = int(os.getenv("CHECK_INTERVAL", "60"))
retry_delay = int(os.getenv("RETRY_DELAY", "5"))

if apprise_url:
    notifier = apprise.Apprise()
    notifier.add(apprise_url)

def get_time():
    return strftime("%Y-%m-%d %H:%M:%S", localtime())

def log(message):
    print(f"[{get_time()}] {message}")

def notify(message, title="Port Checker", notify_type=apprise.NotifyType.INFO):
    notifier.notify(
        body=f"[{get_time()}] {message}",
        title=title,
        notify_type=notify_type
    )

def get_public_ip():
    """Obtains public IP address using an external service"""
    try:
        response = requests.get("https://api.ipify.org?format=text", timeout=5)
        return response.text.strip()
    except Exception as e:
        log(f"❌ Error obtaining public IP address: {e}")
        return "Unknown"
    
def check_port(port=port, domain=domain):
    url = f"https://portchecker.io/api/{domain}/{port}"
    try:
        response = requests.get(url, timeout=10)
        return response.text == "True"
    except Exception as e:
        log(f"❌ API error checking port {port} at {domain}: {e}")
        notify(
            message=f"❌ API error checking port {port} at {domain}: {e}",
            title="API Error",
            notify_type=apprise.NotifyType.FAILURE
        )
        return False

def check_my_port(previous_result):

    resolved_ip = get_public_ip() 

    first_check = previous_result is None

    if first_check and apprise_url:
        notify(
            message=f"🚀 Initializing port-checker for port {port} at {domain} ({resolved_ip})",
            title="Port Checker Initialized",
            notify_type=apprise.NotifyType.INFO
        )

    is_open = check_port(port=port, domain=domain)

    if not is_open and (previous_result is True or first_check):
        log(f"🔍 Port {port} reported closed. Retrying in {retry_delay}s...")
        sleep(retry_delay)
        is_open = check_port(port=port, domain=domain)

        if is_open:
            log(f"🟢 False alarm! Port {port} is actually open at {domain} ({resolved_ip}).")
        else:
            log(f"🔴 Port {port} is not reachable at {domain} ({resolved_ip})")
            if apprise_url:
                if first_check:
                    log(f"📣 Port {port} is currently not reachable at {domain} ({resolved_ip}). Sending initial notification...")
                else:
                    log(f"📣 Port {port} just closed at {domain} ({resolved_ip}). Sending notification...")
                notify(
                    message=f"🔴 Port {port} is not reachable at {domain} ({resolved_ip}).",
                    title="Port Closed",
                    notify_type=apprise.NotifyType.WARNING
                )

    if is_open and (previous_result is False or first_check):
        log(f"🟢 Port {port} is open at {domain} ({resolved_ip})")
        if apprise_url:
            if first_check:
                log(f"📣 Port {port} is currently open at {domain} ({resolved_ip}). Sending initial notification...")
            else:
                log(f"📣 Port {port} just opened at {domain} ({resolved_ip}). Sending notification...")
            notify(
                message=f"🟢 Port {port} is open at {domain} ({resolved_ip})",
                title="Port Open",
                notify_type=apprise.NotifyType.SUCCESS
            )

    return is_open

if __name__ == "__main__":
    previous_result = None
    log(f"🚀 Initializing port-checker v{__version__} for port {port} at {domain} ({get_public_ip()})")
    if not domain:
        log("❌ No domain specified. Please set the DOMAIN environment variable.")
        exit(1)
    if not apprise_url:
        log("⚠️ No APPRISE_URL specified. Notifications will be disabled.")
    
    while True:
        previous_result = check_my_port(previous_result)
        sleep(check_interval)