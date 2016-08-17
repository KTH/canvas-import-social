#! /usr/bin/env python3
from bs4 import BeautifulSoup
from collections import OrderedDict
from datetime import datetime
from json import load as parse_json, dump as dump_json
from os import stat
from os.path import basename
from urllib.parse import quote as urlquote
import optparse
import requests

with open('config.json') as json_data_file:
    configuration = parse_json(json_data_file)
    canvas = configuration['canvas']
    access_token= canvas["access_token"]
    baseUrl = 'https://%s/api/v1/courses/' % canvas.get('host', 'kth.instructure.com')
    header = {'Authorization' : 'Bearer ' + access_token}

def main():
    parser = optparse.OptionParser(
        usage="Usage: %prog [options] course_code")

    parser.add_option('-v', '--verbose',
                      dest="verbose",
                      default=False,
                      action="store_true",
                      help="Print lots of output to stdout"
    )
    parser.add_option('--canvasid', dest='canvasid',
                      help="Canvas id for the course (or use lms api)"
    )

    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error("course_code is required")
    course_code, = args
    course_id = options.canvasid or find_canvas_id(course_code)
    if not course_id:
        print("Canvas course id not given or found")
        exit(1)
    if options.verbose:
        print("Upload to %s (canvas #%s)" % (course_code, course_id))
    course_code = course_code[:6]
    with open('dump/%s/pages.json' % course_code) as json:
        dumpdata = parse_json(json)

    for data in dumpdata:
        if options.verbose:
            print("Should upload", data)

        # Use the Canvas API to insert the page
        #POST /api/v1/courses/:course_id/pages
        #    wiki_page[title]
        #    wiki_page[body]
        #    wiki_page[published]
        html = BeautifulSoup(open("dump/%s/pages/%s.html" % (course_code, data['slug'])), "html.parser")
        for link in html.findAll(href=True):
            linkdata = next(filter(lambda i: i['url'] == link['href'], data['links']), None)
            if linkdata['category'] == 'file':
                canvas_url = create_file(course_id, 'dump/%s/pages/%s' % (course_code, linkdata['url']),
                                         basename(linkdata['url']))
                print("Uploaded %s to %s for link" % (link['href'], canvas_url))
                link['href'] = canvas_url
                linkdata['url'] = canvas_url

        for img in html.findAll('img'):
            imgdata = next(filter(lambda i: i['url'] == img['src'], data['links']), None)
            if linkdata['category'] == 'file':
                canvas_url = create_file(course_id, 'dump/%s/pages/%s' % (course_code, imgdata['url']),
                                     basename(imgdata['url']))
                print("Uploaded %s to %s for img" % (img['src'], canvas_url))
                img['src'] = canvas_url
                linkdata['url'] = canvas_url

        for tex in html.findAll('span', attrs={'role': 'formula', 'data-language': 'tex'}):
            img = html.new_tag('img')
            img['src'] = '/equation_images/' + urlquote(tex.text)
            img['alt'] = tex.text
            img['class'] = tex.get('class')
            tex.replace_with(img)
            if options.verbose:
                print("Modified formula %s to: %s" % (tex, img))

        url = baseUrl + '%s/pages' % (course_id)
        print("Should post page to", url)
        payload={
            'wiki_page[title]': data['title'],
            'wiki_page[published]': False,
            'wiki_page[body]': str(html)
        }
        if options.verbose:
            print(payload)
        r = requests.post(url, headers = header, data=payload)
        if r.status_code == requests.codes.ok:
            page_response=r.json()
            if options.verbose:
                print("result of post creating page: %s" % page_response)
            print("Uploaded page to %s" % page_response['html_url'])
            data['url'] = page_response['html_url']
        else:
            print("Failed to upload page %s" % data['title'])
    dumpname = 'dump/%s/zzz-import-%s-%s.json' % (
        course_code, course_code, datetime.now().strftime('%Y%m%d-%H%M%S'))
    with open(dumpname, 'w') as json:
        dump_json(dumpdata, json, indent=4)
    result = create_file(course_id, dumpname, basename(dumpname))
    print('Uploaded final result to %s' % result)

def create_file(course_id, full_folder_name, file_name, verbose=False):
    url = baseUrl + '%s/files' %(course_id)
    statinfo = stat(full_folder_name)
    payload = {
        'name' :  file_name,
        'size' :  statinfo.st_size,
    }
    if verbose:
        print("Upload %s as %s" % (full_folder_name, payload))

    # note that the following must use a "post" and not a "put" operation
    phase1_response = requests.post(url, headers=header, data=payload)
    if phase1_response.status_code != 200:
        print('Error in upload phase 1: %s\n%s' % (phase1_response, phase1_response.text))
        exit(1)

    phase1_response_data=phase1_response.json()
    if verbose:
        print("Phase 1 response: %s" % phase1_response_data)

    upload_url=phase1_response_data['upload_url']
    data = OrderedDict(phase1_response_data['upload_params'])
    data[phase1_response_data['file_param']] = open(full_folder_name, 'rb')
    #data.move_to_end(phase1_response_data['file_param'])
    if verbose:
        print("Post to %s: %s" % (upload_url, data))

    phase2_response=requests.post(upload_url, files=data, allow_redirects=False)
    if phase2_response.status_code >= 400:
        print('Error in upload phase 2: %s\n%s' % (phase2_response, phase2_response.text))
        exit(1)

    if verbose:
        print("Phase 2 should redirect: %s %s" % (phase2_response, phase2_response.headers))

    phase3_response = requests.get(phase2_response.headers.get('Location'), headers=header)
    phase3_data = phase3_response.json()
    if phase1_response.status_code != 200:
        print('Error in upload phase 1: %s\n%s' % (phase1_response, phase1_response.text))
        exit(1)
    if verbose:
        print("Phase 3 response: %s, json: %s" % (phase3_response, phase3_data))

    url = phase3_data['url']
    return url[0:url.find('?')]

def find_canvas_id(coursecode):
    resp = requests.get('http://lms-integration-1-r.referens.sys.kth.se:3000/lms-integration/api/courses/%s' % coursecode[:6])
    if resp.status_code != 200:
        print('Failed to get canvas data for %s' % coursecode[:6]);
        return None
    for j in resp.json():
        if j['sis_course_id'] == coursecode:
            return j['id']
        else:
            print('Ignoring %s' % j['sis_course_id'])
    print('Failed to get canvas data for %s' % coursecode);
    return None


if __name__ == '__main__': main()
