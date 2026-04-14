# Welcome to port-checker!

port-checker is a small utility to check whether a particular port is open at a given hostname. It can be run in two modes:

### CLI Mode
You can run port-checker from the cli by providing a hostname and port number as arguments:

```
python port-checker <host-name> <port>
```

Example:

```
C:\> python port-checker.py google.com 80
🚀 Checking port 80 at google.com (142.251.39.174)
🟢 Port 80 is open at google.com
```

It will check whether the port is accessible from the internet and will let you know if it's open or closed.

### Continuous monitoring
Run without arguments or as a docker container (sample `docker-compose-example.yml` file provided), the app will monitor the provided port periodically and will send notifications via AppRise whenever the port becomes unavailable or comes back online. You just have to populate the appropriate variables in your `docker-compose.yml` file or through an `.env` file (for docker deployments) or by providing a `config.json` file with the settings located in the app root folder (see example `config-example.json` file provided). The following variables are used:

- `HOST_NAME`: host name to monitor (required).
- `PORT`: port number to monitor (optional, default is 80).
- `CHECK_INTERVAL`: interval in seconds for the periodic checks (optional, default is 60s).
- `RETRY_DELAY`: to avoid false alarms or temporary network glitches, upon first failure the app will try to reach the port again after this amount of time (in seconds) before reporting it as down and sending a notification (optional, default is 5s).
- `APPRISE_URL`: AppRise URL to be notified on. Check the [AppRise documentation](https://appriseit.com/services/) for instructions on how to set up your favorite notification service (optional).

### Installation
Clone this repository to your local machine:

```
git clone https://github.com/NakedRoboticCore/port-checker.git
```

Create a Python virtual environment (venv). This will create a folder named `env_name`:

```
python -m venv <env_name>
```

Activate the virtual environment:

```
# Windows:
C:\> <env_name>\Scripts\activate.bat

# Linux:
$ source <env_name>/bin/activate
```

Install dependencies:
```
pip install -r requirements.txt
```

You can then rename the provided `config-example.json` as `config.json` and run the script from the command line.

If you want to run it as a docker container you don't need to create the virtual environment. Just rename the provided `docker-compose-example.yml` as `docker-compose.yml` and run:

```
docker compose up -d
```

You can check the application logs to see if it's running:
```
docker compose logs -f
```
