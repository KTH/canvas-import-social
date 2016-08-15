# canvas-import-social
Import pages (with possible uploaded files) from a dump from social into canvas.
The tool to create the dumps this package works on is a management command included in social.

In social, with production server configuration (i.e. access to production databases), run:

    ./manage.py dump_course_contents $COURSE_CODE

Prepare for running this project as for any python 3 project, something like this:

    virtualenv-3.5 venv
    . ./venv/bin/activate
    pip install -r requirements.txt

Then, in this project, with the dump from above in a directory called
`dump`, and with the folloing information known:

$COURSE_CODE: The code used by KTH for course round,
something like AB1234HT161 for the course round with id 1, starting
fall (HT) 2016 (16) of the course AB1234.
$SLUG: The file name (sans .html) of the file to upload from dump.

    ./src/import_page.py -v $COURSE_CODE $SLUG

This is a work in progress.
