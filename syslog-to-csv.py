#!/usr/bin/env python3

__version__ = "0.1.0"

import sys
import logging
import logging.config
import argparse
import datetime
import pathlib
import log2csv as lc

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def split_daemon(daemon):
    return daemon.split("[")


def main(args):

    logger = logging.getLogger("syslog-to-csv")
    logger.setLevel(args.loglevel)

    deletions_handler = {
        "64charguids": lc.wipe_64charguids_from_string,
        "guids": lc.wipe_guids_from_string,
        "numbers": lc.wipe_numbers_from_string,
    }

    deletions = ["64charguids", "guids", "numbers"]

    syslog_fieldnames = [
        "line_number",
        "line_length",
        "extracted_date",
        "unix_timestamp",
        "real_date",
        "hostname",
        "daemon",
        "wiped_line",
    ]

    logfile = pathlib.Path(args.filename)
    logger.debug(logfile.parent)
    args.filename_path = pathlib.Path(args.filename)

    output_filename = pathlib.Path(f"""{args.csv_file}""")

    csv_writer = lc.get_csv_handle(output_filename, fieldnames=syslog_fieldnames)

    if args.header == "yes":
        csv_writer.writeheader()

    # A syslog line looks like this :
    # Aug 15 08:22:53 debian systemd-modules-load[272]: Inserted module 'ppdev'
    # 0123456789ABCDEF
    # we want to extract the date so we split at 15:
    split_at_column = 15

    open_fn = lc.open_file_handle(args.filename_path)
    with open_fn(args.filename_path, "rb") as file:
        for line_number, line in enumerate(file):
            try:
                line = line.decode("utf-8")
            except Exception as e:
                logger.warning(
                    f"Could not convert line number {line_number} to utf-8: ({line}) {e}"
                )
                continue
            logger.debug(f"""DAVE type line: {type(line)}""")
            length_of_line = len(line)
            logger.debug(f"processing: {line_number} ({line})")
            if length_of_line <= split_at_column:
                logger.warning(
                    f"squib: line {line_number} is not minimum length of ({split_at_column}) characters"
                )
                continue
            line = line.rstrip()
            line_dict = {}
            logger.debug(f"""Processing: {line_number} __ {line} __""")
            date, remains_of_line = line[:split_at_column], line[split_at_column:]
            logger.debug(
                f"""line number: {line_number}: remains_of_line is of type: {type(remains_of_line)}"""
            )
            r = remains_of_line
            logger.debug(f"""type r: {type(r)}""")
            w = r.lstrip(" ")
            logger.debug(f"""type w: {type(w)}""")
            z = w.split(" ", 2)
            if len(z) >= 2:
                hostname = z[0]
                d = split_daemon(z[1])
                daemon = d[0]
            else:
                logger.warning(
                    f"squib: line {line_number} does not have host/daemon portion."
                )
                continue

            for deletion in deletions:
                logger.debug(f"""Deletion: {deletion}""")
                w = deletions_handler[deletion](w)
            try:
                (real_date, real_datetime, real_datetime_obj) = lc.fix_syslog_date(
                    date, args.base_year
                )
                line_dict["line_number"] = {
                    "line_number": line_number,
                    "line_length": length_of_line,
                    "real_date": real_datetime,
                    "unix_timestamp": real_datetime_obj.timestamp(),
                    "extracted_date": date,
                    "hostname": hostname,
                    "daemon": daemon,
                    "wiped_line": w,
                }
                logger.debug(f"Writing: {line_number} ({line})")
                csv_writer.writerow(line_dict["line_number"])
            except Exception as e:
                logger.warning(f"Could not parse: {line_number} ({line}) {e}")


if __name__ == "__main__":
    """This is executed when run from the command line"""
    parser = argparse.ArgumentParser()

    parser.add_argument("filename", help="a syslog file")

    parser.add_argument(
        "-d",
        "--debug",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
        help="debug(-d, --debug, etc)",
    )

    parser.add_argument(
        "--base-year",
        action="store",
        dest="base_year",
        default=datetime.datetime.now().year,
        help="--base-year 2021",
    )

    parser.add_argument(
        "--csv-file",
        action="store",
        dest="csv_file",
        default="syslog.csv",
        help="--csv-file  <csv output file name>",
    )

    parser.add_argument(
        "--log-type",
        action="store",
        dest="log_type",
        default="syslog",
        help="--log-type syslog ",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__),
    )

    parser.add_argument(
        "--header",
        action="store",
        dest="header",
        default="yes",
        help="--header no <dont print the header in the csv",
    )

    args = parser.parse_args()

    main(args)
