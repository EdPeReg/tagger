#!/usr/bin/env python3

"""
This program will tag any media files, that includes photos and videos,
and move those tagged files to a specific folder, this is more to tag
and backup media files.

This is only for linux and it needs to have exiftool installed in order to work
"""

# TODO: When the subpocess executes, get the real id process
# and kill it after the new tag is entered, this is to close the instance
# TODO: Dont open a new window when watching the foto, use the same instance
# because when there are multiple photos there are multiple instances open
# it is reponsability of the person to close them
# TODO: Check if you have exiftool isntalled or not
# TODO: Add windows support, exiftool is also available on windows but xdg-open
# no, make it crossplatform

import re
import mimetypes
import datetime
import subprocess
import shlex
import shutil
import argparse
import tempfile

from pathlib import Path


class Tagger:
    """
    The tagger will have the ability to tag media files and move
    them to a specific folder to backup

    Attributes:
        __path: Path that contains media files to be tagged
        __date: Store the modification date to find media files
        __files: A list of filepaths that will contains only the media files
        according to the __date
        __tag_file: Dictionary that stores the tag and all the filepaths corresponding
        to that tag
    """

    def __init__(self):
        self.__args = None
        self.__path: Path
        self.__temp_path = tempfile.TemporaryDirectory(
            dir=Path(__file__).parent.absolute()
        )
        self.__date: str = ""
        self.__files: list[Path] = []
        self.__tag_file: dict[str, list[Path]] = {}
        self.__check_args()
        # self.__check_requirements()

    @property
    def path(self):
        return self.__path

    @path.setter
    def path(self, value):
        self.__path = value

    @property
    def date(self):
        return self.__date

    @date.setter
    def date(self, value):
        self.__date = value

    @property
    def files(self):
        return self.__files

    @files.setter
    def files(self, value):
        self.__files = value

    def find_files(self) -> None:
        """
        Will find all the media files under certain date (given as argument)
        """

        # We have to initialize the mime type before using it
        mimetypes.init()
        # For each file in the current path, check if it is a file and not a folder
        regular_files = [f for f in self.path.iterdir() if f.is_file()]

        if not regular_files:
            print(f"There are not files at folder {self.path}")
        else:
            # We want to find only media files, the mime type returns a tuple, and the [0]
            # tell us if it is an image or a video
            pattern_mime = r"image\/|video\/"
            self.files = [
                reg_file
                for reg_file in regular_files
                # We use the "" if we have None, if it is none it will take the empty string
                # In this way we avoid errors when it is None
                if re.search(pattern_mime, mimetypes.guess_type(reg_file)[0] or "")
            ]

            aux = []
            for path in self.files:
                # Get modification time, for linux there is no easy way to get the creation time
                # https://stackoverflow.com/questions/237079/how-do-i-get-file-creation-and-modification-date-times
                # Because of this, we will use modification time
                modif_time = datetime.datetime.fromtimestamp(path.stat().st_mtime)

                if self.date == modif_time.strftime("%Y-%m-%d"):
                    new_file_name = path.name.replace(" ", "_")
                    new_path = path.with_name(new_file_name)
                    path.rename(new_path)
                    aux.append(new_path)
            self.files[:] = aux

    def tag_file(self):
        """
        Given an image or video, it will promp to enter a new tag to the file, the tag should
        not contain espaces. For example:

        <year>_<event>
        2023_cumple_juan

        It will add then this tag to the file, preserving the modification date/time
        """
        for f in self.files:
            print(f"Opening {f}")

            # Copy to temp folder to speed things, specially when the file is using mtp
            shutil.copy2(f, self.__temp_path.name)
            f = Path(self.__temp_path.name).joinpath(f.name)
            # Open the file with the default program
            process_xdg, args = self.__run_subprocess(
                f"xdg-open '{f}'", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            process_xdg.wait()
            self.__check_subprocess(process_xdg, args)

            option = input("Skip file? [y/n]: ")
            # TODO: Repetead way to check input, maybe refactor it?
            if option.lower() == "y":
                print("Skipping file...")
                continue

            option = input("Remove file? [y/n]: ")
            if option.lower() == "y":
                print(f"Removing {f} ...")
                f.unlink(missing_ok=True)
            else:
                # Get the tag Subject
                process_exif, args = self.__run_subprocess(
                    f"exiftool -s3 -Subject '{f}'",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                tag, _ = process_exif.communicate()
                process_exif.wait()
                self.__check_subprocess(process_exif, args)

                change_tag = False
                tag = tag.strip()
                if tag:
                    option = input(f"File already has a tag: {tag}, change it? [y/n]: ")
                    if option.lower() == "y":
                        change_tag = True
                else:
                    change_tag = True

                if change_tag:
                    tag = input("Enter the tag for the file without spaces: ")
                    # Create the new tag
                    process_exif, args = self.__run_subprocess(
                        f"exiftool -P -Subject={tag} '{f}'"
                    )
                    process_exif.wait()
                    self.__check_subprocess(process_exif, args)

                # Multiple files can have the same tag
                if tag in self.__tag_file:
                    self.__tag_file[tag].append(f)
                else:
                    self.__tag_file[tag] = [f]

    def remove_backup(self) -> None:
        """
        Every time the exiftool runs, it creates a backup from the original file, these files
        have an specific format like "file.jpg_original" , we don't need them because
        we are already preserving the time of the files
        """
        for path in Path(self.__temp_path.name).glob("*.*_original"):
            print(f"Removing {path}")
            # If the file doesn't exist, don't throw an exception
            path.unlink(missing_ok=True)

    def move_files(self) -> None:
        """
        All files already tagged will be moved to a new path, for example
        if one file has the tag "fish" and this path given is: "~/Documents"
        A new folder will be created (if it is necessary) "~/Documents/fish"
        """
        print("\n======================")

        for tag, filepaths in self.__tag_file.items():
            print(f"\nTAG: {tag} at file(s): ", *filepaths, sep="\n")
            print(f"Total files: {len(filepaths)}")
            path_dst = Path(
                input("Enter the absolute path to the folder to move the files: ")
            ).expanduser()

            path_dst = path_dst.joinpath(tag)

            if not path_dst.exists():
                print(
                    f"Destination folder {path_dst} doesn't exist, creating folder...\n"
                )
                Path.mkdir(path_dst, parents=True, exist_ok=True)

            for filepath in filepaths:
                print(f"Moving {filepath} -> {path_dst}")
                shutil.move(filepath, path_dst)
                # Remove the file from the original path
                Path.unlink(self.path.joinpath(filepath.name), missing_ok=True)
            print(f"{len(filepaths)} files moved")
        self.__temp_path.cleanup()

    def __check_args(self) -> None:
        """
        Check if the arguments are valid, it raise an exception if an argument
        is not valid
        """

        parser = argparse.ArgumentParser(description="Tagger software")
        parser.add_argument(
            "folder_path",
            type=self.__callback_path,
            help="Absolute folder path that contains media files to tag, \
            if folder has spaces it should be quoted",
        )
        parser.add_argument(
            "date",
            type=self.__callback_date,
            help="Modification date in format YYYY-MM-DD",
        )
        self.__args = parser.parse_args()
        self.path = self.__args.folder_path
        self.date = self.__args.date.strftime("%Y-%m-%d")

    def __callback_path(self, path: str) -> Path:
        p = Path(path).expanduser()
        if p.exists():
            return p
        raise argparse.ArgumentTypeError(f"Path {path} does not exist")

    def __callback_date(self, date: str):
        try:
            # Check if the given date matches with the given date sintax
            return datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError as error:
            print(error)
            raise argparse.ArgumentTypeError(
                f"Invalid date {date}, should be YYYY-MM-DD"
            )

    def __run_subprocess(
        self, cmd: str, stdout=None, stderr=None, text=None
    ) -> tuple[subprocess.Popen, list[str]]:
        """
        Private method that opens a process to run it.

        ARGS:
            cmd: Current string command to be run
            stdout and stderr: By default is None, but subprocess.DEVNULL can be
            used to supress stdout and stderr

        RETURNS:
            An instance of a Popen object and its arguments
        """
        # Get as a list the command string
        args = shlex.split(cmd)
        process = subprocess.Popen(args, stdout=stdout, stderr=stderr, text=text)
        return (process, args)

    def __check_subprocess(self, process, args: list[str]) -> None:
        """
        Private method that check if the process somehow didn't finish
        correctly, if that's the case, it kills the process

        ARGS:
            process: Object returned by running subprocess.Popen
            args: List of arguments used by process

        """
        # Check if child process is terminated
        if process.poll() is None:
            print("Killing the process commad: ", *args, end="")
            print(f" with PID {process.pid}")
            process.kill()

        # The process terminates but with an error code
        if process.returncode != 0:
            print("ERROR, Process with command: ", *args, end="")
            print(f"\nended with return code {process.returncode}")
            raise subprocess.CalledProcessError(
                process.returncode, "".join(args), output=None, stderr=None
            )


def main():
    tagger = Tagger()
    tagger.find_files()
    if tagger.files:
        tagger.tag_file()
        tagger.remove_backup()
        tagger.move_files()
    else:
        print(f"There are no files with date {tagger.date} at path {tagger.path}")


if __name__ == "__main__":
    main()
