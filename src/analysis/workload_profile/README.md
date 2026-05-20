# Create and parse Xdebug trace files

## Setup Xdebug to generate trace files

For this instruction file the PHP framework [Symfony](https://github.com/symfony/symfony) is used as an example application. You can use any PHP application of your choice.

The instructions are tested to be working on:
- Debian 13 (20260316-2418) via HVM on both x86 and arm64 architectures. The detailed OS information is as follows:
```bash
$ cat /etc/os-release
PRETTY_NAME="Debian GNU/Linux 13 (trixie)"
NAME="Debian GNU/Linux"
VERSION_ID="13"
VERSION="13 (trixie)"
VERSION_CODENAME=trixie
DEBIAN_VERSION_FULL=13.4
ID=debian
HOME_URL="https://www.debian.org/"
SUPPORT_URL="https://www.debian.org/support"
BUG_REPORT_URL="https://bugs.debian.org/"
```
- Ubuntu Server 24.04 LTS via HVM on x86 architecture. The detailed OS information is as follows:
```bash
$ cat /etc/os-release
PRETTY_NAME="Ubuntu 24.04.4 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.4 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
```

### Install PHP and Xdebug

#### Debian 13 PHP 8.2

```bash
# PHP 8.2 is not shipped with Debian 13. To install PHP 8.2:
sudo apt install apt-transport-https lsb-release ca-certificates wget -y
sudo wget -O /etc/apt/trusted.gpg.d/php.gpg https://packages.sury.org/php/apt.gpg
sudo sh -c 'echo "deb https://packages.sury.org/php/ $(lsb_release -sc) main" > /etc/apt/sources.list.d/php.list'
sudo apt update && sudo apt install -y git php8.2 php8.2-xdebug \
    php8.2-xml php8.2-gmp php8.2-mbstring php8.2-curl php8.2-intl composer
```

#### Debian 13 PHP 8.4

```bash
# PHP 8.4 is shipped with Debian 13.
sudo apt update && sudo apt install -y git php8.4 php8.4-xdebug \
    php8.4-xml php8.4-gmp php8.4-mbstring php8.4-curl composer
```

#### Ubuntu 24.04 PHP 8.2

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:ondrej/php -y
sudo apt update && sudo apt install -y git php8.2 php8.2-xdebug \
    php8.2-xml php8.2-gmp php8.2-mbstring php8.2-curl php8.2-intl composer
```

#### Ubuntu 24.04 PHP 8.4

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:ondrej/php -y
sudo apt update && sudo apt install -y git php8.4 php8.4-xdebug \
    php8.4-xml php8.4-gmp php8.4-mbstring php8.4-curl composer
```

### Generate Xdebug trace files

These commands are not specific to either Debian or Ubuntu.

```bash
# Setup PHP project. Here we use Symfony as an example.
git clone https://github.com/symfony/symfony.git
cd symfony
composer install

# For output_dir, you can specify any directory you prefer.
# Here we use /tmp/xdebug_traces as an example.
mkdir -p /tmp/xdebug_traces

# The starting point of the application for validating the functionality of
# this instruction file is the PHPUnit test suite. You can run it on any
# starting point of the application.
php -d xdebug.mode=trace \
    -d xdebug.start_with_request=yes \
    -d xdebug.output_dir=/tmp/xdebug_traces \
    -d xdebug.trace_format=1 \
    ./vendor/bin/simple-phpunit

ls -l /tmp/xdebug_traces # List the generated Xdebug trace files
```

## Parse Xdebug trace files
Copy the generated Xdebug trace files to your local machine. You can use `scp` or any other file transfer method you prefer. Then you have to unzip (if the files are zipped) and parse the trace files using the `parse_xdebug_trace.py` script.
