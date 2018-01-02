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
    lmsapiurl = configuration['lmsapi']

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
    parser.add_option('--dir', dest='dumpdir', default='dump',
                      help="Directory to read dumps from"
    )
    parser.add_option('--nop', dest='nop', default=False, action='store_true',
                      help="Only show canvas course for course round."
    )

    options, args = parser.parse_args()
    if options.canvasid and len(args) != 1:
        parser.error("Exactly one course_code is required when giving canvas id")
    elif len(args) == 0:
        parser.error("At least one course_code is required")

    for course_code in args:
        course_id = options.canvasid or find_canvas_id(course_code)
        if not course_id:
            print("Canvas course id not given or found")
            exit(1)
        dumpdir = options.dumpdir
        if options.verbose:
            print("Upload to %s (canvas #%s) from %s" % (
                course_code, course_id, dumpdir))
        if options.nop:
            continue

        course_code = course_code[:6]
        with open('%s/%s/pages.json' % (dumpdir, course_code)) as json:
            dumpdata = parse_json(json)

        uploaded_files = {}
        for data in dumpdata:
            if options.verbose:
                print("Should upload", data)

            # Use the Canvas API to insert the page
            #POST /api/v1/courses/:course_id/pages
            #    wiki_page[title]
            #    wiki_page[body]
            #    wiki_page[published]
            html = BeautifulSoup(open("%s/%s/pages/%s.html" % (dumpdir, course_code, data['slug'])), "html.parser")
            for link in html.findAll(href=True):
                linkdata = next(filter(lambda i: i['url'] == link['href'], data['links']), None)
                if linkdata and linkdata.get('category') == 'file':
                    canvas_url = uploaded_files.get(link['href'])
                    if not canvas_url:
                        canvas_url = create_file(course_id, '%s/%s/pages/%s' % (dumpdir, course_code, linkdata['url']),
                                                 basename(linkdata['url']))
                        print("Uploaded %s to %s for link" % (link['href'], canvas_url))
                        uploaded_files[link['href']] = canvas_url
                    else:
                        print("%s is allready at %s" % (link['href'], canvas_url))
                    link['href'] = canvas_url
                    linkdata['url'] = canvas_url

            for img in html.findAll('img'):
                imgdata = next(filter(lambda i: i['url'] == img.get('src'), data['links']), {})
                if imgdata.get('category') == 'file':
                    canvas_url = uploaded_files.get(img['src'])
                    if not canvas_url:
                        canvas_url = create_file(course_id, '%s/%s/pages/%s' % (dumpdir, course_code, imgdata['url']),
                                                 basename(imgdata['url']))
                        print("Uploaded %s to %s for img" % (img['src'], canvas_url))
                        uploaded_files[img['src']] = canvas_url
                    else:
                        print("%s is allready at %s" % (img['src'], canvas_url))
                    img['src'] = canvas_url
                    imgdata['url'] = canvas_url

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
                print("Failed to upload page %s: %s" % (data['title'], r))
        dumpname = '%s/%s/zzz-import-%s-%s.json' % (
            dumpdir, course_code, course_code, datetime.now().strftime('%Y%m%d-%H%M%S'))
        with open(dumpname, 'w') as json:
            dump_json(dumpdata, json, indent=4)
        result = create_file(course_id, dumpname, basename(dumpname))
        print('Uploaded final result to %s' % result)

def create_file(course_id, full_folder_name, file_name, verbose=False):
    url = baseUrl + '%s/files' %(course_id)
    try:
        statinfo = stat(full_folder_name)
    except:
        try:
            full_folder_name = full_folder_name.replace('+', '%20')
            statinfo = stat(full_folder_name)
        except:
            from urllib.parse import unquote
            full_folder_name = unquote(full_folder_name)
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
        print('Error in upload phase 3: %s\n%s' % (phase1_response, phase1_response.text))
        exit(1)
    if verbose:
        print("Phase 3 response: %s, json: %s" % (phase3_response, phase3_data))

    url = phase3_data['url']
    return url[0:url.find('?')]

def find_canvas_id(coursecode, forterm='HT17'):
    print('Url: %s' % ('%s/courses/%s' % (lmsapiurl, coursecode[:6])))
    resp = requests.get('%s/courses/%s' % (lmsapiurl, coursecode[:6]))
    if resp.status_code != 200:
        print('Failed to get canvas data for %s: %s' % (coursecode[:6], resp));
        return None
    data = resp.json()
    if len(data) == 1:
        return data[0]['id']
    found = {}
    for j in data:
        if j['sis_course_id'] == coursecode:
            return j['id']
        if j['sis_course_id'][:10] == coursecode + forterm:
            found[j['sis_course_id']] = j['id']
        #else:
        #    print('Ignoring %s' % j['sis_course_id'])
    if len(found) == 1:
        print("This should be simple: %s" % found)
        return found.popitem()[1]
    print('Failed to get canvas data for %s; got: %s' % (coursecode, data));
    return None


if __name__ == '__main__': main()
