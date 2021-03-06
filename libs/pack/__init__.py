#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'mark'
__email__ = 'mark@zamplus.com'

import logging
logger = logging.getLogger(__name__)

import os
import zipfile
from libs.env.hdfs import hdfs
from libs.env import debug


LIB_NAME = 'libs'


def zip_dir(src_dir, dst_name, new_root_name=None, ignore_dir=['__pycache__']):
    zipf = zipfile.ZipFile(dst_name, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(src_dir):
        if not files:
            continue
        if os.path.basename(root) in ignore_dir:
            continue
        for file in files:
            arcname = os.path.join(os.path.relpath(root, src_dir), file)
            if new_root_name:
                arcname = os.path.join(new_root_name, arcname)
            zipf.write(os.path.join(root, file), arcname)
    zipf.close()

@debug.pycharm_skip
def pack_libs(overwrite = True):
    path = os.path.join(os.getcwd(), LIB_NAME)
    zip_path = f'{LIB_NAME}.zip'
    zip_dir(path, zip_path)

    from conf.hadoop import HDFS_CODE_CACHE
    if hdfs.exists(HDFS_CODE_CACHE):
        if not overwrite:
            logger.info(f'{zip_path} is exist! {HDFS_CODE_CACHE}')
            return
        hdfs.rm(HDFS_CODE_CACHE)
    hdfs.mkdir(os.path.dirname(HDFS_CODE_CACHE))

    hdfs.put(zip_path, HDFS_CODE_CACHE)

    logger.info(f'success upload {zip_path} to {HDFS_CODE_CACHE}')
