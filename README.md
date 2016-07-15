# canvas-import-social
Import pages (with possible uploaded files) from a dump from social into canvas.
The tool to create the dumps this package works on is a management command included in social.

In social, with production server configuration (i.e. access to production databases), run:

    ./manage.py dump_course_contents $COURSE_CODE

This is a work in progress.
