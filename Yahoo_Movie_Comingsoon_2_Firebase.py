# encoding: utf-8
#——————利用爬蟲程式將即將上映的電影資訊儲存到Firebase資料庫中————————#

# 導入Firebase所需要的套件
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# 導入爬蟲所需要的程式
import requests
from bs4 import BeautifulSoup

# 導入Google Cloud Client的函示庫
import google.cloud

# 將爬蟲需要的headers定義好先
request_headers = {'User-Agent': 'Mozilla/5.0'}

# 導入時間的套件
import datetime

# Firebase金鑰認證，驗證身分，只需要驗證一次就好了
cred = credentials.Certificate('GOOGLE FIREBASE API KEY')
firebase_admin.initialize_app(cred)
db = firestore.client()

# 每次先將資料中的「即將上映電影」以及「隨機推薦電影清單/即將上映」清空
path = "隨機推薦電影清單/即將上映"
doc_ref = db.document(path)
doc_ref.delete()

path = "隨機推薦電影清單/即將上映(中文)"
doc_ref = db.document(path)
doc_ref.delete()

# ——————利用批次檔刪除Firebase資料庫裡面原有的時刻表————————#
def delete_collection(coll_ref, batch_size):
    docs = coll_ref.limit(batch_size).get()
    deleted = 0
    for doc in docs:
        doc.reference.delete()
        deleted = deleted + 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)


movie_coming_soon = db.collection('即將上映電影')
delete_collection(movie_coming_soon, 10)


# ——————取得即將上映的每一部電影的電影名稱並上傳到Firebase————————#
def get_movie_name(movie_url, how_many_movie):
    res = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(res.text, 'lxml')
    ch = soup.find_all('div', 'movie_intro_info_r')
    global movie
    for s in ch:
        s2 = s.find('h1')  # 取出中文
        s3 = s.find('h3')  # 取出英文

        if len(s2.text) != 0 and len(s3.text) != 0:

            if how_many_movie == 0:
                # 英文名稱傳到即將上映
                doc_Movie_Soon = {  # 傳送每一筆電影的「英文名稱」到 隨機推薦電影清單/上映中
                    "%s" % (how_many_movie): "%s" % (s3.text.replace('/', '|'))
                }
                doc_ref_Movie_Soon = db.collection("隨機推薦電影清單").document("即將上映")
                doc_ref_Movie_Soon.set(doc_Movie_Soon)

                # 中文名稱傳到上映中
                doc_Movie_Soon = {  # 傳送每一筆電影的「英文名稱」到 隨機推薦電影清單/上映中
                    "%s" % (how_many_movie): "%s" % (s2.text.replace('/', '|')+'$%$'+s3.text.replace('/', '|'))
                }
                doc_ref_Movie_Soon = db.collection("隨機推薦電影清單").document("即將上映(中文)")
                doc_ref_Movie_Soon.set(doc_Movie_Soon)

                # 傳到Firebase上面
            doc_ref = db.collection("即將上映電影").document("%s" % (s3.text.replace('/', '|')))  # 用英文名字來找這一部電影
            try:
                doc = doc_ref.get()
                upload_name_already_had(movie_url, how_many_movie, s2, s3)  # 若Firebase中已經存在這一部電影了
            except google.cloud.exceptions.NotFound:
                upload_name_new(movie_url, how_many_movie, s2, s3)  # 若Firebase中還沒有存在這一部電影
        else:
            movie-=1


#——————上傳即將上映的電影類型，電影的預告URL，電影圖片的URL————————#
def upload(movie_url,eng_name):
    get_movie_type(movie_url,str(eng_name))             #取得電影類型
    get_movie_previewUrl(movie_url,str(eng_name))       #取得電影預告URL
    get_movie_picurl(movie_url,str(eng_name))           #取得電影圖片URL
    get_age_limit(movie_url, str(eng_name))             #取得電影的年齡分級限制
    get_release_time(movie_url, str(eng_name))


# ——————取得即將上映的每一部電影的電影類型並上傳到Firebase————————#
def get_movie_type(movie_url, movie_name):
    res = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    ch = soup.find_all('div', class_='level_name')

    type_string = ""
    for t in ch:
        if t.find('a', class_='gabtn') != None:
            each_type = t.find('a', class_='gabtn').text.replace('\n', '').replace(' ', '')
            each_type_split = each_type.split('/')
            if len(each_type_split) > 0:
                for s in each_type_split:
                    type_string = type_string + " " + s
            else:
                type_string = type_string + " " + each_type

    # 以下將「即將上映電影的類型」更新到Firebase
    doc_Movie_Info_Type = {  # 傳送每一筆電影"類型"到 Movie_Info-"各部電影名稱"
        "Movie_Type": "%s" % (type_string)
    }

    doc_ref_Movie_Info_Type = db.collection("即將上映電影").document("%s" % (movie_name))
    doc_ref_Movie_Info_Type.update(doc_Movie_Info_Type)


# ——————取得即將上映的每一部電影的電影預告URL並上傳到Firebase————————#
def get_movie_previewUrl(movie_url, movie_name):
    res = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    ch = soup.find_all('ul', 'movie_tab_list')

    list1 = []
    for s in ch:
        s2 = s.find_all('li')
    if 'href' in str(s2[1]):  # 當預告沒有被撤下來的時候
        s3 = str(s2[1]).split('href="')[1]
        list1.append(s3)

        # 以下將「正在上映電影的預告片URL」更新到Firebase
        doc_Movie_Info_Preview = {  # 傳送每一筆電影"預告"到 「上映中電影」"各部電影名稱"
            "Movie_PreviewURL": "%s" % (str(list1[-1]).split('"')[0])
        }

        doc_ref_Movie_Info_Preview = db.collection("即將上映電影").document("%s" % (movie_name))
        doc_ref_Movie_Info_Preview.update(doc_Movie_Info_Preview)


# ——————取得即將上映的每一部電影的電影圖片URL並上傳到Firebase————————#
def get_movie_picurl(movie_url, movie_name):
    res = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    ch = soup.find_all('div', 'movie_intro_foto')

    count = 0
    for s in ch:
        s2 = s.find('img')
        url = s2.get('src')

    doc_Movie_Info_Image_Url = {  # 傳送每一筆電影"圖片網址"到 Movie_Info-"各部電影名稱"
        "Movie_ImageURL": "%s" % (url)
    }

    # 以下將「正在上映電影的圖片URL」更新到Firebase
    doc_Movie_Info_Image_Url = {  # 傳送每一筆電影"圖片網址"到 Movie_Info-"各部電影名稱"
        "Movie_ImageURL": "%s" % (url)
    }

    doc_ref_Movie_Info_Img_Url = db.collection("即將上映電影").document("%s" % (movie_name))
    doc_ref_Movie_Info_Img_Url.update(doc_Movie_Info_Image_Url)


# ——————取得上映中每一部電影的年齡分級限制並上傳到Firebase————————#
def get_age_limit(movie_url, movie_name):
    res = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(res.text, 'lxml')
    ch = soup.find_all('div', 'movie_intro_info_r')
    s4 = ''
    for result in ch:
        age_result = result.find('div')

    if str(age_result.get('class')).split("\'")[1] == '':
        s4 = '0+'
    else:
        s4 = str(age_result.get('class')).split("\'")[1].split('_')[1] + '+'

    # 以下將「正在上映電影的年齡分級」更新到Firebase
    doc_Movie_Info_Image_Url = {  # 傳送每一筆電影"圖片網址"到 Movie_Info-"各部電影名稱"
        "Movie_AgeLimit": "%s" % (s4)
    }

    doc_ref_Movie_Info_Img_Url = db.collection("即將上映電影").document("%s" % (movie_name))
    doc_ref_Movie_Info_Img_Url.update(doc_Movie_Info_Image_Url)


# ——————取得上映中每一部電影的上映時間並上傳到Firebase————————#
def get_release_time(movie_url, movie_name):
    res = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(res.text, 'lxml')
    ch = soup.find_all('div', 'movie_intro_info_r')
    come_time = ''
    for result in ch:
        come_time = result.find('span')

    if come_time == '':
        come_time = '未知上映時間'
    else:
        come_time = come_time.text.split('上映日期：')[1]

    # 以下將「正在上映電影的年齡分級」更新到Firebase
    doc_Movie_Info_Image_Url = {  # 傳送每一筆電影"圖片網址"到 Movie_Info-"各部電影名稱"
        "Movie_ReleaseTime": "%s" % (come_time)
    }

    doc_ref_Movie_Info_Img_Url = db.collection("即將上映電影").document("%s" % (movie_name))
    doc_ref_Movie_Info_Img_Url.update(doc_Movie_Info_Image_Url)


# ——————用電影的英文名字檢索若這一部電影的名稱已經存在Firebase的話用update更新————————#
def upload_name_already_had(movie_url, how_many_movie, chinese_name, eng_name):
    Eng_Name = eng_name.text.replace('/', '|')
    Chi_Name = chinese_name.text.replace('/', '|')

    # 以下將「即將上映電影的中英文名字資訊」上傳到Firebase
    doc_Movie_Info_Name = {  # 傳送每一筆電影"名稱(中+英)"到 即將上映電影-"各部電影名稱"
        "Movie_Name_Chinese": "%s" % (Chi_Name),
        "Movie_Name_English": "%s" % (Eng_Name)
    }
    doc_ref_Movie_Info_Name = db.collection("即將上映電影").document("%s" % (Eng_Name))
    doc_ref_Movie_Info_Name.update(doc_Movie_Info_Name)

    upload(movie_url, Eng_Name)  # 取得其他相關的正在上映中的電影資訊


# ——————用電影的英文名字檢索若這一部電影的名稱還不在在Firebase的話用create新增————————#
def upload_name_new(movie_url, how_many_movie, chinese_name, eng_name):
    Eng_Name = eng_name.text.replace('/', '|')
    Chi_Name = chinese_name.text.replace('/', '|')

    # 以下將「隨機推薦即將上映的電影的列表」上傳到Firebase
    doc_Movie_Soon = {  # 傳送每一筆電影"英文名稱"到 Movie_Now-"上映中"
        "%s" % (how_many_movie): "%s" % (Eng_Name)
    }
    doc_ref_Movie_Soon = db.collection("隨機推薦電影清單").document("即將上映")
    doc_ref_Movie_Soon.update(doc_Movie_Soon)

    # 以下將「隨機推薦即將上映的電影的列表」上傳到Firebase
    doc_Movie_Soon = {  # 傳送每一筆電影"英文名稱"到 Movie_Now-"上映中"
        "%s" % (how_many_movie): "%s" % (Chi_Name+'$%$'+Eng_Name)
    }
    doc_ref_Movie_Soon = db.collection("隨機推薦電影清單").document("即將上映(中文)")
    doc_ref_Movie_Soon.update(doc_Movie_Soon)

    # 以下將「正在上映電影的中英文名字資訊」上傳到Firebase
    doc_Movie_Info_Name = {  # 傳送每一筆電影"名稱(中+英)"到 Movie_Info-"各部電影名稱"
        "Movie_Name_Chinese": "%s" % (Chi_Name),
        "Movie_Name_English": "%s" % (Eng_Name)
    }
    doc_ref_Movie_Info_Name = db.collection("即將上映電影").document("%s" % (Eng_Name))
    doc_ref_Movie_Info_Name.create(doc_Movie_Info_Name)

    upload(movie_url, Eng_Name)  # 取得其他相關的正在上映中的電影資訊


#——————讀取Yahoo「即將上映」的電影每一頁的每一部電影並取得其鏈接————————#
def get_movie_coming(month):
    url = 'https://movies.yahoo.com.tw/movie_comingsoon.html?month='+str(month)
    headers = {'User-Agent': 'Mozilla/5.0'}
    global movie
    for i in range(1,10,1):
        res = requests.get(url+'&page='+str(i),headers = headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch = soup.find_all('div','release_movie_name')
        for s in ch:
            s2=s.find('a')
            get_movie_name(str(s2.get('href')),movie)
            movie+=1


#——————得到當下的時間的天數，判斷這個月是否過了一半，若沒過一半則只看這個月的若超過一半則看這個月和下個月的————————#
x = datetime.datetime.now()
global movie
movie = 0
# if(int(x.day)>=15):
get_movie_coming(str(x.month))
if int(x.month)==12:
    get_movie_coming(str(1))
else:
    get_movie_coming(str(int(x.month)+1))
# else:
#     get_movie_coming(str(x.month))


#——————去本週新片裡面看看是否有電影是即將上映的————————#
for i in range(1,5,1): #1到5每次加1
    res = requests.get('https://movies.yahoo.com.tw/movie_thisweek.html?page='+str(i),headers=request_headers)
    soup = BeautifulSoup(res.text,'lxml')
    info = soup.find_all('div','release_info')
    for s in info:
        time_info = s.find('div','release_movie_time')
        time_processed = time_info.text.split(' ')[-1]
        year = int(time_processed.split('-')[0])
        month = int(time_processed.split('-')[1])
        day = int(time_processed.split('-')[2])
        if year > int(x.year): #電影上映的年份比今年大(跨年)
            ch = s.find('div','en')
            s2= ch.find('a')
            get_movie_name(str(s2.get('href')),movie) #呼叫get_movie_name函數取得每一步電影的名稱
            movie+=1
        elif (year == int(x.year)) and (month > int(x.month)): #電影上映的年份一樣，月份比這個月大
            ch = s.find('div', 'en')
            s2 = ch.find('a')
            get_movie_name(str(s2.get('href')), movie)  # 呼叫get_movie_name函數取得每一步電影的名稱
            movie += 1
        elif (year == int(x.year)) and (month == int(x.month)) and (day > int(x.day)):  #電影上映的年份一樣，月份也一樣，天數比較大
            ch = s.find('div', 'en')
            s2 = ch.find('a')
            get_movie_name(str(s2.get('href')), movie)  # 呼叫get_movie_name函數取得每一步電影的名稱
            movie += 1
