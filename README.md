# Overview

This WordPress backup script is a simple and reliable backup creating a solution for WordPress projects. It takes the copy of static files from WordPress folder + DB (MySQL) dump, uploads archive to remote FTP server and deletes old backups from FTP server.

The solution is tested with:
  * Python 3.6.8
  * CentOS 7
  * MariaDB 5.5.68
  * WordPress 6.0.2

Also should work smoothly with other Linux distributives and versions of software.

# Before start
Before using the script, you should order FTP hosting and ensure it is available for you and has enough disk space.

Examples of such FTP service providers:
https://abc-server.com/en/services/backup/
https://www.defendhosting.com/ftp-hosting/
https://deltahost.com/ftp.html

# Installation
1. Ensure that the following dependencies are installed:
  * python3
  * python libs
   * dotenv
   * ftplib
  * mysqldump

2. Clone the repository.
```
cd ~
git clone ....
cd buckup_script
```

3. Edit .env with the correct FTP server configuration.
```
FTP_HOST=
FTP_USER=
FTP_PASSWORD=
```

4. Add new cronjob for running the buckup script.
Avaliable script parameters:
  * project_name - WordPress website name. Will be used in buckap names.
  * wp_dir - Path to WP web-ite directory with wp-config.php
  * keep_copies - Number of copies on FTP server. For example, if passed 5 (default) - at 6 run, the script will delete the oldest copy from the FTP server.
  * custom_folders_to_backup -  Custom website folders to backup (list). By default script copies only "wp-content" folder and "wp-config.php" file.

Cron job example.
```
0 4 * * * cd ~/buckup_script && python3 wp_buckup.py --project_name chinchilla_tech --wp_dir "/srv/chinchilla/" --keep_copies 10
```

