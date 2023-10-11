""" Copy a file with callback (E.g. update a progress bar) """

# based on flutefreak7's answer at StackOverflow
# https://stackoverflow.com/questions/29967487/get-progress-back-from-shutil-file-copy-thread/48450305#48450305
# License: MIT License

import os
import pathlib
import shutil

# how many bytes to read at once?
# shutil.copy uses 1024 * 1024 if _WINDOWS else 64 * 1024
# however, in my testing on MacOS with SSD, I've found a much larger buffer is faster
DEFAULT_BUFFER_SIZE = 4096 * 1024


class SameFileError(OSError):
    """Raised when source and destination are the same file."""


class SpecialFileError(OSError):
    """Raised when trying to do a kind of operation (e.g. copying) which is
    not supported on a special file (e.g. a named pipe)"""


def copy_with_callback(
    src, dest, callback=None, follow_symlinks=True, buffer_size=DEFAULT_BUFFER_SIZE
):
    """ Copy file with a callback. 
        callback, if provided, must be a callable and will be 
        called after ever buffer_size bytes are copied.

    Args:
        src: source file, must exist
        dest: destination path; if an existing directory, 
            file will be copied to the directory; 
            if it is not a directory, assumed to be destination filename
        callback: callable to call after every buffer_size bytes are copied
            callback will called as callback(bytes_copied since last callback, total bytes copied, total bytes in source file)
        follow_symlinks: bool; if True, follows symlinks
        buffer_size: how many bytes to copy before each call to the callback, default = 4Mb
    
    Returns:
        Full path to destination file

    Raises:
        FileNotFoundError if src doesn't exist
        SameFileError if src and dest are the same file
        SpecialFileError if src or dest are special files (e.g. named pipe)

    Note: Does not copy extended attributes, resource forks or other metadata.
    """

    srcfile = pathlib.Path(src)
    destpath = pathlib.Path(dest)

    if not srcfile.is_file():
        raise FileNotFoundError(f"src file `{src}` doesn't exist")

    destfile = destpath / srcfile.name if destpath.is_dir() else destpath

    if destfile.exists() and srcfile.samefile(destfile):
        raise SameFileError(
            f"source file `{src}` and destinaton file `{dest}` are the same file."
        )

    # check for special files, lifted from shutil.copy source
    for fname in [srcfile, destfile]:
        try:
            st = os.stat(str(fname))
        except OSError:
            # File most likely does not exist
            pass
        else:
            if shutil.stat.S_ISFIFO(st.st_mode):
                raise SpecialFileError(f"`{fname}` is a named pipe")

    if callback is not None and not callable(callback):
        raise ValueError("callback is not callable")

    if not follow_symlinks and srcfile.is_symlink():
        if destfile.exists():
            os.unlink(destfile)
        os.symlink(os.readlink(str(srcfile)), str(destfile))
    else:
        size = os.stat(src).st_size
        with open(srcfile, "rb") as fsrc:
            with open(destfile, "wb") as fdest:
                _copyfileobj(
                    fsrc, fdest, callback=callback, total=size, length=buffer_size
                )
    shutil.copymode(str(srcfile), str(destfile))
    return str(destfile)


def _copyfileobj(fsrc, fdest, callback, total, length):
    """ copy from fsrc to fdest

    Args:
        fsrc: filehandle to source file
        fdest: filehandle to destination file
        callback: callable callback that will be called after every length bytes copied
        total: total bytes in source file (will be passed to callback)
        length: how many bytes to copy at once (between calls to callback)
    """
    copied = 0
    while True:
        buf = fsrc.read(length)
        if not buf:
            break
        fdest.write(buf)
        copied += len(buf)
        if callback is not None:
            callback(len(buf), copied, total)


if __name__ == "__main__":

    from tqdm import tqdm

    srcfile = "/media/jonathan/02B9-7570/DCIM/100GOPRO/GX012300.MP4"
    destfile = "/media/jonathan/8447-CBBE/GX012300.MP4"
    bufsize = None

    bufsize = bufsize or DEFAULT_BUFFER_SIZE
    size = os.stat(srcfile).st_size

    follow_symlinks = True

    bar_format = "{desc}: {percentage:3.0f}% |{bar}| Elapsed: {elapsed} - Remaining:{remaining}"
    with tqdm(total=size, bar_format=bar_format) as bar:
        dest = copy_with_callback(
            srcfile,
            destfile,
            follow_symlinks=follow_symlinks,
            callback=lambda copied, total_copied, total: bar.update(copied),
            buffer_size=bufsize,
        )
