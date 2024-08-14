#!/bin/bash

#
#   Clair Kronk
#   13 August 2024
#   wikibase_build.sh
#

# Rebuild.
php /var/www/html/maintenance/rebuildall.php

# Run jobs.
php /var/www/html/maintenance/runJobs.php --memory-limit 512M

# Initialize site stats.
php /var/www/html/maintenance/initSiteStats.php --update

# Run rebuild script.
php /var/www/html/maintenance/sql.php /var/www/html/rebuildWikibaseIdCounters.sql

# Import constraint statements.
php /var/www/html/maintenance/run.php WikibaseQualityConstraints:ImportConstraintStatements.php

# Run command to insert new entities (items, properties, lexemes), per Phabricator ticket here:
# https://phabricator.wikimedia.org/T368164
php /var/www/html/maintenance/run.php sql --query "INSERT INTO wb_id_counters (id_type, id_value) VALUES ('wikibase-item', (SELECT COALESCE(MAX(CAST(SUBSTRING(page_title, 2) AS UNSIGNED)), 0) FROM page WHERE page_namespace = 120)) ON DUPLICATE KEY UPDATE id_value = (SELECT COALESCE(MAX(CAST(SUBSTRING(page_title, 2) AS UNSIGNED)), 0) FROM page WHERE page_namespace = 120);"
php /var/www/html/maintenance/run.php sql --query "INSERT INTO wb_id_counters (id_type, id_value) VALUES ('wikibase-property', (SELECT COALESCE(MAX(CAST(SUBSTRING(page_title, 2) AS UNSIGNED)), 0) FROM page WHERE page_namespace = 122)) ON DUPLICATE KEY UPDATE id_value = (SELECT COALESCE(MAX(CAST(SUBSTRING(page_title, 2) AS UNSIGNED)), 0) FROM page WHERE page_namespace = 122);"
php /var/www/html/maintenance/run.php sql --query "INSERT INTO wb_id_counters (id_type, id_value) VALUES ('wikibase-lexeme', (SELECT COALESCE(MAX(CAST(SUBSTRING(page_title, 2) AS UNSIGNED)), 0) FROM page WHERE page_namespace = 146)) ON DUPLICATE KEY UPDATE id_value = (SELECT COALESCE(MAX(CAST(SUBSTRING(page_title, 2) AS UNSIGNED)), 0) FROM page WHERE page_namespace = 146);"

# Run rebuild script.
php /var/www/html/maintenance/sql.php /var/www/html/rebuildWikibaseIdCounters.sql

# Import constraint statements.
php /var/www/html/maintenance/run.php WikibaseQualityConstraints:ImportConstraintStatements.php

# Update search index configuration.
php /var/www/html/extensions/CirrusSearch/maintenance/UpdateSearchIndexConfig.php --startOver

# Rebuild search indices.
php /var/www/html/extensions/CirrusSearch/maintenance/ForceSearchIndex.php

# Run jobs (necessary for autocomplete and search to function).
php /var/www/html/maintenance/runJobs.php --memory-limit 512M