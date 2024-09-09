#
#   Modified from: 
#   https://gist.github.com/Monal5031/85b94de036369e0676e8e5b1646cef6d
#

import os

windows_line_ending = b'\r\n'
linux_line_ending = b'\n'

def convert(directory_in_str):
    all_files = []

    for root, dirs, files in os.walk(directory_in_str):
        for name in files:
            full_path = os.path.join(root, name)
            all_files.append(full_path)

    for filename in all_files:
        with open(filename, 'rb') as f:
            content = f.read()
            content = content.replace(windows_line_ending, linux_line_ending)

        try:
            with open(filename, 'wb') as f:
                f.write(content)
        except PermissionError:
            pass