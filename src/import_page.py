#! /usr/bin/env python3
from bs4 import BeautifulSoup
from json import load as parse_json
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


if __name__ == '__main__': main()
