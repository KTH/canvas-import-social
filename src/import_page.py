#! /usr/bin/env python3
from bs4 import BeautifulSoup
from collections import OrderedDict
from json import load as parse_json
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
        usage="Usage: %prog [options] course_id course_code module filename")

    parser.add_option('-v', '--verbose',
                      dest="verbose",
                      default=False,
                      action="store_true",
                      help="Print lots of output to stdout"
    )
    
    options, args = parser.parse_args()
    if len(args) != 4:
        parser.error("course_id, course_code, module, and filename are required")
    course_id, course_code, module, filename = args
    if options.verbose:
        print("Upload", filename, "to", course_id, course_code, module)

    with open('dump/%s/pages.json' % course_code) as json:
        data = parse_json(json)
    data = next(filter(lambda i: i['slug'] == filename, data), None)
    if not data:
        print("Page", filename, "to upload not found in dump")
        exit(1)
    elif options.verbose:
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

    for img in html.findAll('img'):
        imgdata = next(filter(lambda i: i['url'] == img['src'], data['links']), None)
        if linkdata['category'] == 'file':
            canvas_url = create_file(course_id, 'dump/%s/pages/%s' % (course_code, imgdata['url']),
                                     basename(imgdata['url']))
            print("Uploaded %s to %s for img" % (img['src'], canvas_url))
            img['src'] = canvas_url

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
            print("result of post creating page: " + page_response)
        print("Uploaded page to %s" % page_response['html_url'])

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
    return phase3_data['preview_url']


if __name__ == '__main__': main()
