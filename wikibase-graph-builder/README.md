# Wikibase Graph Builder

Note that this section of the application is extremely tentative. Currently to run, you do the following (tested on Windows only!):

1. Run `docker-compose build` in this directory.
2. Run `docker-compose up` in this directory. You can check the status of this command by prefixing it with `strace`.
3. Enter the container on the command-line.
4. Run `npm run dev -- --host` in the directory `/srv/wikidata-graph-builder`.
5. Visit `http://localhost:5173/wikidata-graph-builder/` in your browser.