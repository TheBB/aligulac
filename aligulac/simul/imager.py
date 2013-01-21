#!/usr/bin/python3

import subprocess
from urllib.request import urlopen, Request
from urllib.parse import urlencode
import base64
import json

class Struct:
    pass

class Image:

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self._texts = []
        self._rectangles = []

    def add_text(self, text, left, top, left_align=True):
        fname = 'imgur/temp/' + str(len(self._texts)) + '.png'

        args = ['convert']
        args += ['-size', '200x30']
        args += ['xc:transparent']
        args += ['-draw', 'text 0,20 \'' + text + '\'']
        args += [fname]
        subprocess.call(args)

        args = ['convert']
        args += ['-trim', fname, fname]
        subprocess.call(args)

        args = ['identify', fname]
        s = subprocess.check_output(args).decode().split(' ')
        s = [int(x) for x in s[2].split('x')]

        struct = Struct()
        struct.top = top
        if left_align:
            struct.left = left
        else:
            struct.left = left - s[0]
        struct.width = s[0]
        struct.height = s[1]
        struct.fname = fname

        self._texts.append(struct)

    def add_rectangle(self, left, top, right, bottom, fill, stroke=(0,0,0)):
        struct = Struct()
        struct.top = top
        struct.left = left
        struct.right = right
        struct.bottom = bottom
        struct.fill = fill
        struct.stroke = stroke
        self._rectangles.append(struct)

    def make(self, fname):
        args = ['convert']
        args += ['-size', str(self.width) + 'x' + str(self.height)]
        args += ['xc:transparent']

        for text in self._texts:
            args += ['-draw']
            args += ['image over ' + str(text.left) + ',' + str(text.top) +\
                    ' 0,0 ' + text.fname]
        
        for rect in self._rectangles:
            args += ['-fill', 'rgb' + str(rect.fill)]
            args += ['-stroke', 'rgb' + str(rect.stroke)]
            args += ['-draw']
            args += ['rectangle ' + str(rect.left) + ',' + str(rect.top) + ' '\
                    + str(rect.right) + ',' + str(rect.bottom)]

        args += ['imgur/' + fname + '.png']
        subprocess.call(args)

        return 'imgur/' + fname + '.png'

def make_match_image(m):
    clarity = 75

    im = Image(700,35)
    im.add_text(m.get_player(0).name, 5, 5, True)
    im.add_text(m.get_player(1).name, 695, 5, False)

    instances = sorted(m._outcomes, key=lambda a: a[1]-a[2], reverse=True)
    prev = 5
    dist = 690
    for inst in instances:
        next = round(prev + dist * inst[0])
        red = round(((255-clarity)*inst[1]) / (inst[1]+inst[2]))
        blue = round(((255-clarity)*inst[2]) / (inst[1]+inst[2]))
        if inst[1] > inst[2]:
            red += clarity
        else:
            blue += clarity
        im.add_rectangle(prev, 20, next, 30, (red,0,blue), (0,0,0))
        prev = next

    return im.make('match')

def imgur_upload(fname):
    pic = open(fname, 'rb')
    s = base64.b64encode(pic.read())
    pic.close()

    url = 'http://api.imgur.com/2/upload.json'
    params = dict()
    params['key'] = '1823d9d2c867036ca98771dd21bb8eaa'
    params['image'] = s
    data = urlencode(params).encode('ascii')
    req = Request(url, data)
    response = urlopen(req)

    response = response.read().decode()
    with open('testimgur', 'w') as f:
        f.write(response)

    response = json.loads(response)
    return response['upload']['links']['original']

if __name__ == '__main__':
    imgur_upload('imgur/lee_snip.png')
