import requests
import apprise
import os, sys, dns.resolver
from time import localtime, sleep, strftime

__version__ = "0.0.6"
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

def send_notification(message, title="Port Checker", notify_type=apprise.NotifyType.INFO):
    notifier.notify(
        body=f"[{get_time()}] {message}",
        title=title,
        notify_type=notify_type
    )

def resolve_host_name(host_name):
    try:
        my_resolver = dns.resolver.Resolver()
        my_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
        answers = my_resolver.resolve(host_name, 'A')
        return answers[0].to_text()
    except Exception as e:
        log(f"❌ Error resolving host name {host_name}: {e}")
        return "unknown"

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
        send_notification(
            message=f"❌ API error checking port {port} at {host_name}: {e}",
            title="API Error",
            notify_type=apprise.NotifyType.FAILURE
        )
        return False

def check_my_port(previous_result):

    ip_address = resolve_host_name(host_name)
    public_ip = get_public_ip()

    if ip_address != public_ip:
        if previous_result != "DNS_WAIT":
            log(f"⚠️ DNS Mismatch: DNS says {ip_address} but your IP is {public_ip}. Your IP may have changed and DNS records have not updated yet.")
            log("🕒 Skipping port check to avoid false alarms until DNS propagates.")
            send_notification(
                message=f"⚠️ DNS Mismatch: DNS says {ip_address} but your IP is {public_ip}. Your IP may have changed and DNS records have not updated yet.",
                title="DNS Mismatch",
                notify_type=apprise.NotifyType.WARNING
            )
        return "DNS_WAIT"
    else:
        if previous_result == "DNS_WAIT":
            log(f"✅ DNS Resolved: DNS now resolves to {ip_address} which matches your IP {public_ip}. Resuming port checks.")
            send_notification(
                message=f"✅ DNS Resolved: DNS now resolves to {ip_address} which matches your IP {public_ip}. Resuming port checks.",
                title="DNS Resolved",
                notify_type=apprise.NotifyType.SUCCESS
            )

    first_check = previous_result is None

    is_open = check_port(port=port, host_name=host_name)

    if not is_open and (previous_result is True or first_check):
        log(f"🔍 Port {port} reported closed. Retrying in {retry_delay}s...")
        sleep(retry_delay)
        is_open = check_port(port=port, host_name=host_name)

        if is_open:
            log(f"🟢 False alarm! Port {port} is actually open at {host_name} ({ip_address}).")
        else:
            log(f"🔴 Port {port} is not reachable at {host_name} ({ip_address})")
            if apprise_url:
                if first_check:
                    log(f"📣 Port {port} is currently not reachable at {host_name} ({ip_address}). Sending initial notification...")
                else:
                    log(f"📣 Port {port} just closed at {host_name} ({ip_address}). Sending notification...")
                send_notification(
                    message=f"🔴 Port {port} is not reachable at {host_name} ({ip_address}).",
                    title="Port Closed",
                    notify_type=apprise.NotifyType.WARNING
                )

    if is_open and (previous_result is False or first_check):
        log(f"🟢 Port {port} is open at {host_name} ({ip_address})")
        if apprise_url:
            if first_check:
                log(f"📣 Port {port} is currently open at {host_name} ({ip_address}). Sending initial notification...")
            else:
                log(f"📣 Port {port} just opened at {host_name} ({ip_address}). Sending notification...")
            send_notification(
                message=f"🟢 Port {port} is open at {host_name} ({ip_address})",
                title="Port Open",
                notify_type=apprise.NotifyType.SUCCESS
            )

    return is_open

if __name__ == "__main__":
    if len(sys.argv) == 1:
        previous_result = None
        if not host_name:
            log("❌ No host name specified. Please set the HOST_NAME environment variable.")
            sys.exit(1)
        ip_address = resolve_host_name(host_name)
        log(f"🚀 Initializing port-checker v{__version__} for port {port} at {host_name} ({ip_address})")
        log(f"⏱️ Check interval: {check_interval}s")
        if not apprise_url:
            log("⚠️ No APPRISE_URL specified. Notifications will be disabled.")
        else:
            send_notification(
                message=f"🚀 Initializing port-checker v{__version__} for port {port} at {host_name} ({ip_address}). Check interval: {check_interval}s",
                title="Port Checker Initialized",
                notify_type=apprise.NotifyType.INFO
            )            
        
        while True:
            previous_result = check_my_port(previous_result)
            sleep(check_interval)

    if len(sys.argv) == 3:
        host_name = sys.argv[1]
        if len(host_name.split(".")) < 2:
            print("❌ Invalid host name. Please provide a valid host name.")
            sys.exit(1)
        ip_address = resolve_host_name(host_name)
        try:
            port = int(sys.argv[2])
        except ValueError:
            print("❌ Invalid port number. Please provide a valid integer for the port.")
            sys.exit(1)
        print(f"🚀 Checking port {port} at {host_name} ({ip_address})")
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
