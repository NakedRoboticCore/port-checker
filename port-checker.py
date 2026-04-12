import requests
import apprise
import os, sys
from time import localtime, sleep, strftime

__version__ = "0.0.5"
host_name = os.getenv("HOST_NAME", "")
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
    """Obtains public IP address using multiple fallback services"""
    services = [
        "https://api.ipify.org?format=text",
        "https://ident.me",
        "https://ifconfig.me/ip",
        "https://icanhazip.com"
    ]
    
    for url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.text.strip()
        except Exception:
            log(f"⚠️ Failed to get public IP from {url}, trying next service...")
            continue
            
    log("❌ All public IP services failed.")
    return "Unknown"
    
def check_port(port=port, host_name=host_name):
    url = f"https://portchecker.io/api/{host_name}/{port}"
    try:
        response = requests.get(url, timeout=10)
        return response.text == "True"
    except Exception as e:
        log(f"❌ API error checking port {port} at {host_name}: {e}")
        notify(
            message=f"❌ API error checking port {port} at {host_name}: {e}",
            title="API Error",
            notify_type=apprise.NotifyType.FAILURE
        )
        return False

def check_my_port(previous_result):

    resolved_ip = get_public_ip() 

    first_check = previous_result is None

    if first_check and apprise_url:
        notify(
            message=f"🚀 Initializing port-checker {__version__} for port {port} at {host_name} ({resolved_ip}). Check interval: {check_interval}s",
            title="Port Checker Initialized",
            notify_type=apprise.NotifyType.INFO
        )

    is_open = check_port(port=port, host_name=host_name)

    if not is_open and (previous_result is True or first_check):
        log(f"🔍 Port {port} reported closed. Retrying in {retry_delay}s...")
        sleep(retry_delay)
        is_open = check_port(port=port, host_name=host_name)

        if is_open:
            log(f"🟢 False alarm! Port {port} is actually open at {host_name} ({resolved_ip}).")
        else:
            log(f"🔴 Port {port} is not reachable at {host_name} ({resolved_ip})")
            if apprise_url:
                if first_check:
                    log(f"📣 Port {port} is currently not reachable at {host_name} ({resolved_ip}). Sending initial notification...")
                else:
                    log(f"📣 Port {port} just closed at {host_name} ({resolved_ip}). Sending notification...")
                notify(
                    message=f"🔴 Port {port} is not reachable at {host_name} ({resolved_ip}).",
                    title="Port Closed",
                    notify_type=apprise.NotifyType.WARNING
                )

    if is_open and (previous_result is False or first_check):
        log(f"🟢 Port {port} is open at {host_name} ({resolved_ip})")
        if apprise_url:
            if first_check:
                log(f"📣 Port {port} is currently open at {host_name} ({resolved_ip}). Sending initial notification...")
            else:
                log(f"📣 Port {port} just opened at {host_name} ({resolved_ip}). Sending notification...")
            notify(
                message=f"🟢 Port {port} is open at {host_name} ({resolved_ip})",
                title="Port Open",
                notify_type=apprise.NotifyType.SUCCESS
            )

    return is_open

if __name__ == "__main__":
    if len(sys.argv) == 1:
        previous_result = None
        log(f"🚀 Initializing port-checker v{__version__} for port {port} at {host_name} ({get_public_ip()})")
        log(f"⏱️ Check interval: {check_interval}s")
        if not host_name:
            log("❌ No host name specified. Please set the HOST_NAME environment variable.")
            sys.exit(1)
        if not apprise_url:
            log("⚠️ No APPRISE_URL specified. Notifications will be disabled.")
        
        while True:
            previous_result = check_my_port(previous_result)
            sleep(check_interval)

    if len(sys.argv) == 3:
        host_name = sys.argv[1]
        if len(host_name.split(".")) < 2:
            print("❌ Invalid host name. Please provide a valid domain or IP address.")
            sys.exit(1)
        try:
            port = int(sys.argv[2])
        except ValueError:
            print("❌ Invalid port number. Please provide a valid integer for the port.")
            sys.exit(1)
        print(f"🚀 Checking port {port} at {host_name} ({get_public_ip()})")
        is_open = check_port(port=port, host_name=host_name)
        if is_open:
            print(f"🟢 Port {port} is open at {host_name}")
            sys.exit(0)
        else:
            print(f"🔴 Port {port} is closed at {host_name}")
            sys.exit(1)
    else:
        print("Usage:")
        print("  To run continuously with environment variables: python port-checker.py")
        print("  To check a specific host and port once: python port-checker.py <host_name> <port>")
        sys.exit(1)
