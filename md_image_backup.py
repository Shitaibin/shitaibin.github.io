# source forkdd from: https://github.com/wangshub/markdown-img-backup
# Thanks WangSong.

# Theory
# filepath -> all markdown file -> using regular expression find markdown image url
# -> download image -> save it

# coding=utf-8
import sys
import os
import re
import requests
import urllib
import urllib2

# encoding=utf8  
reload(sys)  
sys.setdefaultencoding('utf8')   


# search find all markdown files
def search(path, word):
    for filename in os.listdir(path):
        fp = os.path.join(path, filename)
        if os.path.isfile(fp) and word in filename:
            # print "processing:", fp
            download(str(fp))
        elif os.path.isdir(fp):
            search(fp, word)


# download download all image of a file
def download(file_path):
    # filename = "test"
    name = file_path.split(u"/")
    filename = name[-1]
    f_md = open(file_path)

    # all text of md file
    text = f_md.read().decode('utf-8')
    # using regex get all image markdown url
    img_reg = r'\!{1}\[(.*?)\]\((.*?)\)'
    result = re.findall('!\[(.*)\]\((.*)\)', text)

    for i in range(len(result)):
        img_quote = result[i][0]
        img_url = result[i][1]
        # skip qiniu watermark
        if "-own" in img_url:
            img_url = img_url[:-4]

        # extract img name from image url
        urlname = img_url.split(u"/")
        img_name = urlname[len(urlname) - 1]
        # print "name: %s, url: %s" % (img_name, img_url)

        if "lanshiren" in img_name or len(img_name) == 0:
            continue

        # skip download if img is exist
        fpath = 'images/' + img_name
        if os.path.isfile(fpath):
            # print "skip: ",img_name
            continue

        # download img
        print "download img", img_name, img_url
        request = urllib2.Request(img_url)
        response = urllib2.urlopen(request)
        img_contents = response.read()
        
        # write to file
        f_img = open(fpath, 'wb')
        f_img.write(img_contents)
        f_img.close()
    f_md.close()

if __name__ == "__main__":
    print "Image backup start"
    source_dir = "./source"
    if len(sys.argv) > 1:
        source_dir = sys.argv[1]

    search(source_dir, '.md')
    print "Image backup finish"
