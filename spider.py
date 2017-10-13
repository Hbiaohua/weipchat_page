import requests
from urllib.parse import urlencode
from requests.exceptions import ConnectionError
from pyquery import PyQuery as pq
import pymongo

client = pymongo.MongoClient('localhost')
db = client['weichat']

start_url = 'http://weixin.sogou.com/weixin?'
headers = {         #请求参数
    'Cookie':'',     #传入cookie
    'Host': 'weixin.sogou.com',
    'Upgrade-Insecure-Requests':'1',
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3192.0 Safari/537.36'
}
keyword = '风景'
proxy_url = 'http://127.0.0.1:5000/get'
proxy = None  #设置成全局变量
max_count = 5  #最大请求次数

#获取代理（返回获取的ip）
def get_proxy():
    try:
        r = requests.get(proxy_url)
        if r.status_code==200:
            return r.text
    except:
        return None

def get_html(url,count=1):
    print('Crawling',url)       #当前url
    print('Trying Count',count)  #当前请求次数
    global proxy
    if count >= max_count:
        print('Tried Too Many Counts')
        return None
    try:
        if proxy:
            proxies = {
                'http':'http://' + proxy
            }
            r = requests.get(url,allow_redirects=False,headers=headers,proxies=proxies)  #关闭重定向,传入代理
        else:
            r = requests.get(url,allow_redirects=False,headers=headers)
        if r.status_code==200:
            return r.text
        if r.status_code==302:  #ip被封的情况
            print('302')
            proxy = get_proxy()  #获取的代理传入变量
            if proxy:
                print('Using Proxy',proxy)
                return get_html(url)
            else:  #没能获得代理
                print('Get Proxy Fail')
                return None
    except ConnectionError as e:
        print('Error Occurrd',e.args)
        proxy = get_proxy()  #出现连接异常也可，设置代理，再次请求
        count += 1
        return get_html(url,count)   #连接异常，递归调用，再一次请求

#配置索引url
def get_index(keyword,page):
    data = {
        'query': keyword,
        'type': 2,
        'page': page
    }
    queries = urlencode(data)  #将字典转成get请求参数
    url = start_url + queries  #完整url
    html = get_html(url)
    return html

#得到文章链接
def parse_page(html):
    doc = pq(html)
    items = doc('.news-box .news-list li .txt-box h3 a').items()
    for item in items:
        yield item.attr('href')

 #提取文章代码
def datail_page(url):
    try:
        r = requests.get(url)
        if r.status_code==200:
            return r.text
        else:
            return None
    except:
        return None

#解析文章，提取详细信息
def pars_datail(html):
    doc = pq(html)
    title = doc('.rich_media_title').text()
    content = doc('.rich_media_content ').text()
    data = doc('#post-date').text()
    nickname = doc('.rich_media_meta rich_media_meta_link rich_media_meta_nickname').text()
    return {
        'title': title,
        'content': content,
        'data': data,
        'nickname': nickname
    }

#保存文件至mongodb
def save_to_mongodb(data):
    #去重，如果标题重复，只更新数据
    if db['articles'].update({'title': data['title']},{'$set': data},True): #True,没有则插入，存在即更新
        print('Saved to Mongo',data['title'])
    else:
        print('Save Fail',data['title'])

def main():
    for page in range(1,101):
        html = get_index(keyword,page)
        if html:
            aticle_urls = parse_page(html)
            for aticle_url in aticle_urls:
                article_html = datail_page(aticle_url)
                if article_html:
                    data = pars_datail(article_html)
                    print(data)
                    save_to_mongodb(data)

if __name__=='__main__':
    main()