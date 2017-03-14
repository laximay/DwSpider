#!/usr/bin/env python
# encoding: utf-8

import os
import re
import sys
import urllib.parse
import urllib.request
from collections import deque
from urllib.error import URLError, HTTPError
import pymysql
import traceback

from bs4 import BeautifulSoup


class dw_spider:
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
        'Host': 'www.molbase.com',
        'Referer': 'http://www.molbase.com/en/chemical-products.html',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
    baseUrl = "http://www.molbase.com/en/chemical-products.html"
    # 使用队列存放url
    queue = deque()
    # 用于存放所有产品url
    pro_queue = deque()
    # 使用visited防止重复爬同一页面
    visited = set()
    # 使用pro_visited防止重复爬同一页面
    pro_visited = set()

    def __init__(self):
        self.queue.append(self.baseUrl)
        self.cas_img = "cas_img"

    # 获得所有索引，还有所有页码
    def getIndex(self):
        while self.queue:
            print(self.queue[0])
            req = urllib.request.Request(url=self.queue[0], headers=self.headers)
            try:
                response = urllib.request.urlopen(req)
            except  HTTPError as e:
                print('服务器无法完成请求')
                print('Error code: ', e.code)
                continue
            except URLError as e:
                print('访问不到服务器')
                print('Reason: ', e.reason)
                continue
            except BaseException as  e:
                print("系统错误！")
                self.queue = [];
                continue
            else:
                data = response.read()
            type = sys.getfilesystemencoding()  # 转换成本地系统编码 重要代码！！
            data = data.decode(type)
            indexSoup = BeautifulSoup(data, "lxml")
            popUrl = self.queue.popleft()
            self.visited |= {popUrl}  # 移到已访问的集合
            print(self.visited)
            pagination = indexSoup.find('div', {'class', 'caslist'}).find_all(
                href=re.compile("www.molbase.com/en/chemical-products"))  ## 获取当前页面的所有索引，
            for pageUrl in pagination:
                pageUrl_Real = "http:" + pageUrl.get('href')

                if pageUrl_Real not in self.queue and pageUrl_Real not in self.visited:  ## 判断是否访问过，或者已经收录过
                    print("正在收录索引页面：" + pageUrl_Real)
                    self.queue.append(pageUrl_Real)

            # casListBox_tb = indexSoup.html.body.find('table', {'class', 'casListBox'})
            # casListBox = indexSoup.find_all(href=re.compile("moldata"))  ## 获取当前页面的所有索引，
            # for pageUrl in casListBox:
            #     pageUrl_Real = "http:" + pageUrl.get('href')
            #     # print("正在收录产品页面：" + pageUrl_Real)
            #     if pageUrl_Real not in self.pro_queue and pageUrl_Real not in self.pro_queue:  ## 判断是否访问过，或者已经收录过
            #         self.pro_queue.append(pageUrl_Real)
            # print("正在收录产品页面数量：" + str(len(self.pro_queue)))
            # self.readProducts(pageUrl_Real)

    def readProducts(self, productUrl):
        openFlag = 0;  # 打开
        req = urllib.request.Request(url=productUrl, headers=self.headers)
        try:
            response = urllib.request.urlopen(req)
        except:
            print("访问失败，正在重试")
            self.readProducts(productUrl)
        else:
            type = sys.getfilesystemencoding()  # 转换成本地系统编码 重要代码！！
            data = response.read().decode(type)
            indexSoup = BeautifulSoup(data, "lxml")
            iserror = indexSoup.find_all(text=re.compile("异常流量"))
            if len(iserror) > 0:
                print("异常流量")
                self.readProducts(productUrl)
            else:
                self.pro_visited |= {productUrl}  # 移到已访问的集合

                # 获取文字内容，并保存入数据库
                productInfo_html = indexSoup.html.body.find('table', {'class', 'pinfo'})
                productInfo = [];  # 用来存放内容的列表
                if (productInfo_html):
                    rows = productInfo_html.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        cols = [ele.text.strip() for ele in cols]
                        productInfo.append(cols[0])
                    self.saveBrief(productInfo)  # 保存数据进数据库
                else:
                    self.readProducts(productUrl)
                # 保存图片操作
                imgUrl = indexSoup.find("img", id="listimg_1")
                self.saveImg("http:" + imgUrl.get('src'), productInfo[1])

    def mkdir(self, path):
        path = path.strip()
        # 判断路径是否存在
        # 存在     True
        # 不存在   False
        isExists = os.path.exists(path)
        # 判断结果
        if not isExists:
            # 如果不存在则创建目录
            print("正在保存", path)
            # 创建目录操作函数
            os.makedirs(path)
            return True
        else:
            # 如果目录存在则不创建，并提示目录已存在
            print(path, "已经创建")
            return False
            # 传入图片地址，文件名，保存单张图片

    # 保存图片
    def saveImg(self, imageURL, fileName):

        try:
            data = urllib.request.urlopen(imageURL).read()
        except:
            print("访问失败图片，正在重试")
            self.saveImg(imageURL, fileName)
        else:
            fileName = self.cas_img + "/" + fileName + ".png"
        f = open(fileName, 'wb')
        f.write(data)
        print(u"保存了一张图片", fileName)
        f.close()
        # 保存个人简介

    # 保存产品资料
    def saveBrief(self, content):
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', passwd='db19881122',
                               db='dw_spider')
        cur = conn.cursor()
        sql = "INSERT IGNORE INTO `cas_prodecut` VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"  # 保存入数据库
        cur.execute(sql, (content))
        conn.commit()
        cur.close()
        conn.close()


dw_spider = dw_spider()
dw_spider.getIndex()
# dw_spider.mkdir(dw_spider.cas_img)
# dw_spider.readProducts("http://www.molbase.com/en/1932593-57-1-moldata-3925425.html")
