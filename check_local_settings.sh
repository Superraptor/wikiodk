#!/bin/bash

#
#   Clair Kronk
#   12 August 2024
#   check_local_settings.sh
#

# Update LocalSettings.php to allow for entity import.
    # TODO: Add and remove this only when importing.
if grep -Fxq "\$wgWBRepoSettings['allowEntityImport'] = true;" /var/www/html/LocalSettings.php; then
    :
else
    echo "\$wgWBRepoSettings['allowEntityImport'] = true;" >> /var/www/html/LocalSettings.php
fi

# Loop through passed extensions; load if not in LocalSettings.php.
for package in "$@"
do
    if grep -Fxq "wfLoadExtension( '$package' );" /var/www/html/LocalSettings.php; then
        :
    else
        echo "wfLoadExtension( '$package' );" >> /var/www/html/LocalSettings.php
    fi
done