import os, sys, dns.resolver, requests, apprise, json
from time import localtime, sleep, strftime

__version__ = "0.0.8"

class PortChecker:
    def __init__(self):
        self.host_name = ""
        self.port = 80
        self.check_interval = 60
        self.retry_delay = 5
        self.apprise_url = ""
        self.notifier = None
        self.status = None
        self.ip_address = None
        self.public_ip = None

    def load_config(self, config_file="config.json"):
        if os.path.exists(config_file):
            log(f"📁 Loading configuration from {config_file}...")
            with open(config_file, "r") as f:
                config = json.load(f)
                self.host_name = config.get("HOST_NAME", "")
                self.port = config.get("PORT", 80)
                self.check_interval = config.get("CHECK_INTERVAL", 60)
                self.retry_delay = config.get("RETRY_DELAY", 5)
                self.apprise_url = config.get("APPRISE_URL", "")
        else:
            log("🌍 Attemptying to load configuration from environment variables...")
            self.host_name = os.getenv("HOST_NAME", "")
            self.port = int(os.getenv("PORT", "80"))
            self.apprise_url = os.getenv("APPRISE_URL", "")
            self.check_interval = int(os.getenv("CHECK_INTERVAL", "60"))
            self.retry_delay = int(os.getenv("RETRY_DELAY", "5"))

    def check(self):

        self.ip_address = resolve_host_name(self.host_name)
        self.public_ip = get_public_ip()

        if self.ip_address != "unknown" and self.ip_address != self.public_ip:
            if self.status != "DNS_WAIT":
                log(f"⚠️ DNS Mismatch: DNS says {self.ip_address} but your IP is {self.public_ip}. Your IP may have changed and DNS records have not updated yet.")
                log("🕒 Skipping port check to avoid false alarms until DNS propagates.")
                self.send_notification(
                    message=f"⚠️ DNS Mismatch: DNS says {self.ip_address} but your IP is {self.public_ip}. Your IP may have changed and DNS records have not updated yet.",
                    title="DNS Mismatch",
                    notify_type=apprise.NotifyType.WARNING
                )
            self.status = "DNS_WAIT"
            return
        
        if self.ip_address != "unknown" and self.status == "DNS_WAIT":
            log(f"✅ DNS Resolved: DNS now resolves to {self.ip_address} which matches your IP {self.public_ip}. Resuming port checks.")
            self.send_notification(
                message=f"✅ DNS Resolved: DNS now resolves to {self.ip_address} which matches your IP {self.public_ip}. Resuming port checks.",
                title="DNS Resolved",
                notify_type=apprise.NotifyType.SUCCESS
            )

        first_check = self.status is None

        is_open = check_port_once(host_name=self.host_name, port=self.port, notifier=self.notifier)

        if not is_open and (self.status is True or first_check):
            log(f"🔍 Port {self.port} reported closed. Retrying in {self.retry_delay}s...")
            sleep(self.retry_delay)
            is_open = check_port_once(host_name=self.host_name, port=self.port, notifier=self.notifier)

            if is_open:
                log(f"🟢 False alarm! Port {self.port} is actually open at {self.host_name} ({self.ip_address}).")
            else:
                log(f"🔴 Port {self.port} is not reachable at {self.host_name} ({self.ip_address})")
                if self.apprise_url:
                    if first_check:
                        log(f"📣 Port {self.port} is currently not reachable at {self.host_name} ({self.ip_address})")
                    else:
                        log(f"📣 Port {self.port} just closed at {self.host_name} ({self.ip_address})")
                    self.send_notification(
                        message=f"🔴 Port {self.port} is not reachable at {self.host_name} ({self.ip_address}).",
                        title="Port Closed",
                        notify_type=apprise.NotifyType.WARNING,
                        report_success=True
                    )

        if is_open and (self.status is False or first_check):
            log(f"🟢 Port {self.port} is open at {self.host_name} ({self.ip_address})")
            if self.apprise_url:
                if first_check:
                    log(f"📣 Port {self.port} is currently open at {self.host_name} ({self.ip_address})")
                else:
                    log(f"📣 Port {self.port} just opened at {self.host_name} ({self.ip_address})")
                self.send_notification(
                    message=f"🟢 Port {self.port} is open at {self.host_name} ({self.ip_address})",
                    title="Port Open",
                    notify_type=apprise.NotifyType.SUCCESS,
                    report_success=True
                )

        self.status = is_open

    def setup_notifier(self):
        if self.apprise_url:
            self.notifier = apprise.Apprise()
            if not self.notifier.add(self.apprise_url):
                log(f"❌ Failed to add {self.apprise_url} to notifier service, notifications will be disabled")

    def send_notification(self, message, title="Port Checker", notify_type=apprise.NotifyType.INFO, report_success=False):
        if self.notifier:
            status = self.notifier.notify(
                body=f"[{get_time()}] {message}",
                title=title,
                notify_type=notify_type
            )
            if not status:
                log("❌ Failed to send notification")
            elif report_success:
                log("✅ Notification sent successfully")


def get_time():
    return strftime("%Y-%m-%d %H:%M:%S", localtime())

def log(message):
    print(f"[{get_time()}] {message}")

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
    
    failed = False
    for url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                if failed:
                    log(f"✅ Successfully obtained public IP from {url} after previous failures.")
                return response.text.strip()
        except Exception:
            log(f"⚠️ Failed to get public IP from {url}, trying next service...")
            failed = True
            continue
            
    log("❌ All public IP services failed.")
    return "Unknown"
    
def check_port_once(host_name, port, notifier=None):
    url = f"https://portchecker.io/api/{host_name}/{port}"
    try:
        response = requests.get(url, timeout=10)
        return response.text == "True"
    except Exception as e:
        log(f"❌ API error checking port {port} at {host_name}: {e}")
        if notifier:
            notifier.notify(
                body=f"❌ API error checking port {port} at {host_name}: {e}",
                title="API Error",
                notify_type=apprise.NotifyType.FAILURE
            )
        return False

if __name__ == "__main__":

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
        is_open = check_port_once(port=port, host_name=host_name)
        if is_open:
            print(f"🟢 Port {port} is open at {host_name}")
            sys.exit(0)
        else:
            print(f"🔴 Port {port} is closed at {host_name}")
            sys.exit(1)
    
    if len(sys.argv) == 1:
        log(f"🚀 Initializing port-checker v{__version__}")
        my_port_checker = PortChecker()
        my_port_checker.load_config()
        
        if not my_port_checker.host_name:
            log("❌ No host name specified. Please set the HOST_NAME environment variable or provide a host name in config.json.")
            sys.exit(1)
        if 0 < len(my_port_checker.host_name.split(".")) < 2:
            log(f"❌ Invalid host name: {my_port_checker.host_name}. Please provide a valid host name.")
            sys.exit(1)
        log(f"📌 Host name set to {my_port_checker.host_name}")
        if not my_port_checker.port or not isinstance(my_port_checker.port, int) or my_port_checker.port <= 0 or my_port_checker.port > 65535:
            if my_port_checker.port:
                log(f"❌ Invalid port number: {my_port_checker.port}. Please provide a valid port number.")
            else:
                log("❌ No port number specified. Please set the PORT environment variable or provide a port number in config.json.")
            sys.exit(1)
        log(f"📌 Port set to {my_port_checker.port}")
        if not my_port_checker.check_interval or not isinstance(my_port_checker.check_interval, int) or my_port_checker.check_interval <= 0:
            log(f"❌ Invalid check interval: {my_port_checker.check_interval}. Please provide a valid check interval.")
            sys.exit(1)
        log(f"📌 Check interval set to {my_port_checker.check_interval}s")
        if not my_port_checker.retry_delay or not isinstance(my_port_checker.retry_delay, int) or my_port_checker.retry_delay <= 0:
            log(f"❌ Invalid retry delay: {my_port_checker.retry_delay}. Please provide a valid retry delay.")
            sys.exit(1)
        log(f"📌 Retry delay set to {my_port_checker.retry_delay}s")

        if my_port_checker.apprise_url:
            log(f"📌 AppRise URL set to {my_port_checker.apprise_url}")
            ip_address = resolve_host_name(my_port_checker.host_name)
            my_port_checker.setup_notifier()
            my_port_checker.send_notification(
                message=f"🚀 Initializing port-checker v{__version__} for port {my_port_checker.port} at {my_port_checker.host_name} ({ip_address}). Check interval: {my_port_checker.check_interval}s",
                title="Port Checker Initialized",
                notify_type=apprise.NotifyType.INFO
            )            
        else:
            log("⚠️ No APPRISE_URL specified. Notifications will be disabled.")
        
        
        while True:
            my_port_checker.check()
            sleep(my_port_checker.check_interval)

    else:
        print("Usage:")
        print("  To run continuously with environment variables: python port-checker.py")
        print("  To check a specific host and port once: python port-checker.py <host_name> <port>")
        sys.exit(1)
