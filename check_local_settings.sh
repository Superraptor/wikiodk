#!/bin/bash

#
#   Clair Kronk
#   12 August 2024
#   check_local_settings.sh
#

# Loop through passed extensions; load if not in LocalSettings.php.
for package in "$@"
do
    if grep -Fxq "wfLoadExtension( '$package' );" /var/www/html/LocalSettings.php; then
        :
    else
        echo "wfLoadExtension( '$package' );" >> /var/www/html/LocalSettings.php
    fi
done