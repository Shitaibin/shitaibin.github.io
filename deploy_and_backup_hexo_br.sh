#!/bin/bash
#
# source codes upload to github
# website files upload to qiniu

echo "===================== Backup image ====================="
python2 md_image_backup.py

echo "===================== Delete hexo temporary files ====================="
hexo clean

echo "===================== Commit local changes ====================="
git add .
git commit -m 'auto backup'

echo "===================== Push resource to github ====================="
git push origin hexo_resource

echo "===================== Generate website files ====================="
hexo generate

# No need deploy to github
echo "===================== Push website files to github ====================="
hexo d

# echo "===================== Push website files to Qiniu ====================="
# qshell qupload qiniu.conf


