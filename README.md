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
`dump`, run the command:

    ./src/import_course.py -v $COURSE_ROUND_CODE

where $COURSE_ROUND_CODE is The code used for the cavas course that a
given course round at KTH uses.
The format is sometimes used by KOPPS and Social, and looks something
like AB1234HT161 for the course round with ladok round number 1,
starting fall (HT) 2016 (16) of the course AB1234.

This is a work in progress.
