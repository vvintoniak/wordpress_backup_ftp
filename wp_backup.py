#!/usr/bin/python3

from dotenv import dotenv_values
import re
import logging
import argparse
import tarfile
import os.path
import tempfile
import time
import datetime
import os
import ftplib

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("WORDPRESS_BACKUP")
logger.setLevel(logging.INFO)


def parse_arguments():
    parser = argparse.ArgumentParser(description="WordPress website to FTP remote server buckup script")
    parser.add_argument('--project_name', type=str, help='WordPress web-site name', required=True)
    parser.add_argument('--wp_dir', type=str, help='Path to WP web-site directory', required=True)
    parser.add_argument('--keep_copies', type=int, default=5, help='Number of copies on FTP')
    parser.add_argument('--custom_folders_to_backup', type=list, help="Custom web-site folders to backup (list)", default=[])
    return parser.parse_args()


def get_mysql_creds(wp_config):
    define_pattern = re.compile(r"""\bdefine\(\s?\s*('|")(.*)\1\s*,\s?\s*('|")(.*)\3\s?\)\s*;""")
    mysql_vars = {}
    for line in open(wp_config):
        if "DB_" in line:
            for match in define_pattern.finditer(line):
                mysql_vars[match.group(2)] = match.group(4)
    return mysql_vars


def mysql_dump(mysql_config, sql_dump_file_name):
    os.popen("mysqldump -h %s -u %s -p%s %s > %s" % (mysql_config["DB_HOST"], mysql_config["DB_USER"],
                                                     mysql_config["DB_PASSWORD"], mysql_config["DB_NAME"],
                                                     sql_dump_file_name))
    logger.info(f"Database dumped to {sql_dump_file_name}")


def archive_compress(compress_list, archive_path):
    tar = tarfile.open(archive_path, "w:gz")
    for name in compress_list:
        logger.info(f"Adding to an archive {os.path.basename(name)}")
        tar.add(name, arcname=os.path.basename(name))
    tar.close()
    logger.info(f"Archive {archive_path} created")


def ftp_upload(ftp_config, backup_file_path):
    logger.info(f"Connecting to remote FTP server: {ftp_config['FTP_HOST']}")
    session = ftplib.FTP(ftp_config['FTP_HOST'], ftp_config['FTP_USER'], ftp_config['FTP_PASSWORD'])
    file = open(backup_file_path, 'rb')
    logger.info(f"Starting file uploading via FTP: {backup_file_path}")
    session.storbinary(f'STOR {os.path.basename(backup_file_path)}', file)
    logger.info(f"{backup_file_path} - uploaded to remote FTP server")
    file.close()
    session.quit()


def ftp_files_list(ftp_config):
    session = ftplib.FTP(ftp_config['FTP_HOST'], ftp_config['FTP_USER'], ftp_config['FTP_PASSWORD'])
    try:
        files = session.nlst()
        return [f for f in files if f != "." or f != ".."]
    except ftplib.error_perm as resp:
        if str(resp) == "550 No files found":
            print("No files in this directory")
        else:
            raise


def ftp_delete_files(ftp_config, file_to_delete_list):
    session = ftplib.FTP(ftp_config['FTP_HOST'], ftp_config['FTP_USER'], ftp_config['FTP_PASSWORD'])
    for file in file_to_delete_list:
        logger.info(f"Deleting file from FTP: {file}")
        session.delete(file)
        logger.info(f"{file} has been deleted.")


def filter_sort_files(files, backup_file_prefix, timestamp_format):
    project_ftp_files = []
    for file in files:
        if backup_file_prefix in file:
            file_date_dict = {}
            backup_date_str = file.split(backup_file_prefix)[1].split(".tgz")[0]
            backup_date = datetime.datetime.strptime(backup_date_str, timestamp_format)
            file_date_dict["File"] = file
            file_date_dict["Date"] = backup_date
            project_ftp_files.append(file_date_dict)
    project_ftp_files.sort(key=lambda x: x['Date'])
    return [file["File"] for file in project_ftp_files]


def ftp_clean_up(ftp_config, keep_copies, backup_file_prefix, timestamp_format):
    all_remote_files = ftp_files_list(ftp_config)
    all_project_sorted_files = filter_sort_files(all_remote_files, backup_file_prefix, timestamp_format)
    files_keep = all_project_sorted_files[-keep_copies:]
    files_delete = list(set(all_project_sorted_files) - set(files_keep))
    if files_delete:
        ftp_delete_files(ftp_config, files_delete)


if __name__ == '__main__':
    args = parse_arguments()
    wp_mysql_config = get_mysql_creds(args.wp_dir + "/wp-config.php")
    ftp_config = dotenv_values(".env")
    timestamp_format = "%Y%m%d-%H%M%S"
    wp_files_and_folders_to_backup = [
        "wp-content",
        "wp-config.php"
    ]
    wp_files_and_folders_to_backup = wp_files_and_folders_to_backup + args.custom_folders_to_backup
    backup_list = []
    for item in wp_files_and_folders_to_backup:
        backup_list.append(args.wp_dir + item)
    sql_dump_file_name = args.project_name + "_DB_DUMP_" + time.strftime(timestamp_format) + ".sql"
    backup_file_prefix = args.project_name + "_wordpress_backup_"
    backup_file_name = backup_file_prefix + time.strftime(timestamp_format) + ".tgz"
    with tempfile.TemporaryDirectory() as tmpdirname:
        mysql_dump(wp_mysql_config, tmpdirname + "/" + sql_dump_file_name)
        backup_list.append(tmpdirname + "/" + sql_dump_file_name)
        backup_archive_path = tmpdirname + "/" + backup_file_name
        archive_compress(backup_list, backup_archive_path)
        ftp_upload(ftp_config, backup_archive_path)
    ftp_clean_up(ftp_config, args.keep_copies, backup_file_prefix, timestamp_format)
