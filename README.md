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

$COURSE_ID: A numeric course id from canvas
$COURSE_CODE: The code used by KTH for course, something like AB1234.
$MODULE: (TODO, I don't know what this is supposed to be, it is currently unused)
$SLUG: The file name (sans .html) of the file to upload from dump.

    ./src/import_page.py -v $COURSE_ID $COURSE_CODE $MODULE $SLUG

This is a work in progress.
