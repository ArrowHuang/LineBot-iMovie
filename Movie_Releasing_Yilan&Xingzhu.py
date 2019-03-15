# encoding: utf-8
# ——————利用爬蟲程式將上映中的電影資訊儲存到Firebase資料庫中————————#

# 導入Firebase所需要的套件
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# 導入爬蟲所需要的程式
import requests
from bs4 import BeautifulSoup

# 導入時間的套件
import datetime

# 導入Google Cloud Client的函示庫
import google.cloud

# 導入googlemaps的套件
import googlemaps

# 註冊googlemap的API的client
gmaps = googlemaps.Client(key='GOOGLE MAP API KEY')

# 將爬蟲需要的headers定義好先
request_headers = {'User-Agent': 'Mozilla/5.0'}

# Firebase金鑰認證，驗證身分，只需要驗證一次就好了
cred = credentials.Certificate('GOOGLE FIREBASE API KEY')
firebase_admin.initialize_app(cred)
db = firestore.client()


# ——————透過上映中電影首頁的時刻表的網址找到其對應的時刻表資訊————————#
def get_movie_page(how_many_movie,movie_url, chname, enname):
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(movie_url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    ch = soup.find_all('div', 'movie_tab')

    for s in ch:
        s2 = s.find('a')
        x = str(s2.get('href'))
        x = x.split('-')
        get_movie_time(movie_url,x[-1], str(chname), str(enname))



# ——————按照不同地點有什麼電影上映存到Firebase上面————————#
def store_location_and_movie(location,chname,enname):
    doc_ref = db.collection("按地點分電影").document("%s" % (location))
    doc = doc_ref.get()
    if doc.to_dict() != None:
        length = len(doc.to_dict())
        doc_Movie_Now = {  
            "%s" % (length): "%s" % (enname)
        }
        doc_ref_Movie_Now = db.collection("按地點分電影").document(location)
        doc_ref_Movie_Now.update(doc_Movie_Now)
    else:
        doc = doc_ref.get()
        doc_Movie_Now = {  
            "0" : "%s" % (enname)
        }
        doc_ref_Movie_Now = db.collection("按地點分電影").document(location)
        doc_ref_Movie_Now.set(doc_Movie_Now)


# ——————抓取每一部電影在不同影城的時刻資訊並上傳到Firebase上面————————#
def get_movie_time(movie_url, movie_id, chname, enname):
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get('https://movies.yahoo.com.tw/movietime_result.html/id=' + str(movie_id))
    soup = BeautifulSoup(res.text, 'html.parser')
    each_area = soup.find_all('div', class_='area_timebox')
    global how_many_movie
    if len(each_area) > 0:
        has_movie = False
        show_time = 0
        for ch in each_area:
            area_name = ch.find('div', 'area_title')
            if '新竹' in area_name.text.strip() or '宜蘭' in area_name.text.strip():
                has_movie = True
                print(how_many_movie)
                
                if how_many_movie == 0:
                    # 英文名稱傳到上映中
                    doc_Movie_Now = {  # 傳送每一筆電影的「英文名稱」到 隨機推薦電影清單/上映中
                        "%s" % (how_many_movie): "%s" % (enname)
                    }
                    doc_ref_Movie_Now = db.collection("隨機推薦電影清單").document("上映中")
                    doc_ref_Movie_Now.set(doc_Movie_Now)

                    # 中文名稱傳到上映中
                    doc_Movie_Now = {  # 傳送每一筆電影的「英文名稱」到 隨機推薦電影清單/上映中
                        "%s" % (how_many_movie): "%s" % (chname + '$%$' + enname)
                    }
                    doc_ref_Movie_Now = db.collection("隨機推薦電影清單").document("上映中(中文)")
                    doc_ref_Movie_Now.set(doc_Movie_Now)
                    

                # 若是新竹或宜蘭電影院有上映則上傳Firebase
                get_movie_names(movie_url, how_many_movie, chname, enname)

                # 將每個地名放映的電影名稱存在Firebase上面
                store_location_and_movie(area_name.text.strip(),chname, enname)
                
                ch = ch.find_all('ul', 'area_time _c')
                count = []

                for s in ch:
                    s2 = s.find_all('li', 'adds')
                    for s4 in s2:
                        x = s4.find('a').text  # 取得影城名稱
                        adds_href = str(s4.find('a')).split('href="')[1].split('">')[0]

                    s3 = s.find_all('li', 'time _c')
                    for s5 in s3:
                        y = s5.find('ul').text  # 取得電影上映時刻

                    w = ''
                    s4 = s.find_all('div')
                    if len(s4) > 0:
                        for st in s4:
                            if st.text.strip() != '':
                                w = w + st.text.strip() + ' '
                                # print(w)

                    res = requests.get(str(adds_href))
                    soup = BeautifulSoup(res.text, 'html.parser')
                    ch = soup.find_all('div', 'theaterlist_area')
                    for s in ch:
                        s2 = s.find_all('li')
                    z = str(s2[1].text.replace('地址：', ''))

                    place_search = gmaps.places(
                        query=x + ' ' + z,
                        language='zh-TW',
                        type='movie_theater'
                    )

                    movie_theater_name = str(place_search['results'][0]['name']) + '{' + w.strip() + '}'
                    #                     print(x+','+z+','+movie_theater_name)
                    t = db.collection("電影時刻表").document("%s" % (chname))

                    # 將電影的時刻表上傳到Firebase資料庫
                    try:
                        doc = t.get()
                        doc = {
                            "%s" % (movie_theater_name): "%s" % (y)
                        }
                        doc_ref = db.collection("電影時刻表").document("%s" % (chname))
                        doc_ref.update(doc)

                    except google.cloud.exceptions.NotFound:
                        doc = {
                            "%s" % (movie_theater_name): "%s" % (y),
                        }
                        doc_ref = db.collection("電影時刻表").document("%s" % (chname))
                        doc_ref.create(doc)
        
        if has_movie == True and show_time == 0:
            how_many_movie += 1
            show_time += 1


# ——————取得上映中每一部電影的電影名稱並上傳到Firebase————————#
def get_movie_name(movie_url, how_many_movie):
    res = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(res.text, 'lxml')
    ch = soup.find_all('div', 'movie_intro_info_r')

    for s in ch:
        s2 = s.find('h1')  # 取出中文
        s3 = s.find('h3')  # 取出英文
        get_movie_page(how_many_movie, movie_url, str(s2.text), str(s3.text))  # 找到每一部上映中電影的網頁資訊，並找到其中的時刻表的連結


# ——————確定在新竹有這部電影才上傳————————#
def get_movie_names(movie_url, how_many_movie, chname, enname):
    if len(chname) != 0 and len(enname) != 0:

        # 傳到Firebase上面
        doc_ref = db.collection("上映中電影").document("%s" % (enname))  # 用英文名字來找這一部電影
        try:
            doc = doc_ref.get()
            upload_name_already_had(movie_url, how_many_movie, chname, enname)  # 若Firebase中已經存在這一部電影了
        except google.cloud.exceptions.NotFound:
            upload_name_new(movie_url, how_many_movie, chname, enname)  # 若Firebase中還沒有存在這一部電影


# 每次先將資料中的「即將上映電影」以及「隨機推薦電影清單/即將上映」清空
path = "隨機推薦電影清單/上映中"
doc_ref = db.document(path)
doc_ref.delete()

path = "隨機推薦電影清單/上映中(中文)"
doc_ref = db.document(path)
doc_ref.delete()

path = "按地點分電影/宜蘭"
doc_ref = db.document(path)
doc_ref.delete()

path = "按地點分電影/新竹"
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

students_ref = db.collection('電影時刻表')
delete_collection(students_ref, 10)


# ——————利用批次檔刪除Firebase資料庫裡面原有的時刻表————————#
def delete_collection(coll_ref, batch_size):
    docs = coll_ref.limit(batch_size).get()
    deleted = 0
    for doc in docs:
        doc.reference.delete()
        deleted = deleted + 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

students_ref = db.collection('上映中電影')
delete_collection(students_ref, 10)


# ——————上傳電影類型，電影的預告URL，電影圖片的URL以及電影————————#
def upload(movie_url, eng_name):
    get_movie_type(movie_url, str(eng_name))  # 取得電影類型
    get_movie_previewUrl(movie_url, str(eng_name))  # 取得電影預告URL
    get_movie_picurl(movie_url, str(eng_name))  # 取得電影圖片URL
    get_age_limit(movie_url,str(eng_name))      # 取得電影的年齡分級限制


# ——————取得上映中每一部電影的電影類型並上傳到Firebase————————#
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

    # 以下將「正在上映電影的類型」更新到Firebase
    doc_Movie_Info_Type = {  # 傳送每一筆電影"類型"到 Movie_Info-"各部電影名稱"
        "Movie_Type": "%s" % (type_string)
    }

    doc_ref_Movie_Info_Type = db.collection("上映中電影").document("%s" % (movie_name))
    doc_ref_Movie_Info_Type.update(doc_Movie_Info_Type)


# ——————取得上映中每一部電影的電影預告URL並上傳到Firebase————————#
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

        doc_ref_Movie_Info_Preview = db.collection("上映中電影").document("%s" % (movie_name))
        doc_ref_Movie_Info_Preview.update(doc_Movie_Info_Preview)


# ——————取得上映中每一部電影的電影圖片URL並上傳到Firebase————————#
def get_movie_picurl(movie_url, movie_name):
    res = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    ch = soup.find_all('div', 'movie_intro_foto')

    count = 0
    for s in ch:
        s2 = s.find('img')
        url = s2.get('src')

    # 以下將「正在上映電影的圖片URL」更新到Firebase
    doc_Movie_Info_Image_Url = {  # 傳送每一筆電影"圖片網址"到 Movie_Info-"各部電影名稱"
        "Movie_ImageURL": "%s" % (url)
    }

    doc_ref_Movie_Info_Img_Url = db.collection("上映中電影").document("%s" % (movie_name))
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

    doc_ref_Movie_Info_Img_Url = db.collection("上映中電影").document("%s" % (movie_name))
    doc_ref_Movie_Info_Img_Url.update(doc_Movie_Info_Image_Url)


# ——————用電影的英文名字檢索若這一部電影的名稱已經存在Firebase的話用update更新————————#
def upload_name_already_had(movie_url, how_many_movie, chinese_name, eng_name):
    Eng_Name = eng_name
    Chi_Name = chinese_name

    # 以下將「隨機推薦正在上映的電影的列表」上傳到Firebase
    doc_Movie_Now = {  # 傳送每一筆電影的「英文名稱」到 隨機推薦電影清單/上映中
        "%s" % (how_many_movie): "%s" % (Eng_Name)
    }
    doc_ref_Movie_Now = db.collection("隨機推薦電影清單").document("上映中")
    doc_ref_Movie_Now.update(doc_Movie_Now)

    # 以下將「隨機推薦正在上映的電影的列表」上傳到Firebase
    doc_Movie_Now = {  # 傳送每一筆電影的「中文名稱」到 隨機推薦電影清單/上映中(中文)
        "%s" % (how_many_movie): "%s" % (Chi_Name+'$%$'+Eng_Name)
    }
    doc_ref_Movie_Now = db.collection("隨機推薦電影清單").document("上映中(中文)")
    doc_ref_Movie_Now.update(doc_Movie_Now)

    # 以下將「正在上映電影的中英文名字資訊」上傳到Firebase
    doc_Movie_Info_Name = {  # 傳送每一筆電影"名稱(中+英)"到 Movie_Info-"各部電影名稱"
        "Movie_Name_Chinese": "%s" % (Chi_Name),
        "Movie_Name_English": "%s" % (Eng_Name)
    }
    doc_ref_Movie_Info_Name = db.collection("上映中電影").document("%s" % (Eng_Name))
    doc_ref_Movie_Info_Name.update(doc_Movie_Info_Name)

    upload(movie_url, Eng_Name)  # 取得其他相關的正在上映中的電影資訊


# ——————用電影的英文名字檢索若這一部電影的名稱還不在在Firebase的話用create新增————————#
def upload_name_new(movie_url, how_many_movie, chinese_name, eng_name):
    Eng_Name = eng_name
    Chi_Name = chinese_name

    # 以下將「隨機推薦正在上映的電影的列表」上傳到Firebase
    doc_Movie_Now = {  # 傳送每一筆電影"英文名稱"到 Movie_Now-"上映中"
        "%s" % (how_many_movie): "%s" % (Eng_Name)
    }
    doc_ref_Movie_Now = db.collection("隨機推薦電影清單").document("上映中")
    doc_ref_Movie_Now.update(doc_Movie_Now)

    # 以下將「隨機推薦正在上映的電影的列表」上傳到Firebase
    doc_Movie_Now = {  # 傳送每一筆電影的「中文名稱」到 隨機推薦電影清單/上映中(中文)
        "%s" % (how_many_movie): "%s" % (Chi_Name+'$%$'+Eng_Name)
    }
    doc_ref_Movie_Now = db.collection("隨機推薦電影清單").document("上映中(中文)")
    doc_ref_Movie_Now.update(doc_Movie_Now)

    # 以下將「正在上映電影的中英文名字資訊」上傳到Firebase
    doc_Movie_Info_Name = {  # 傳送每一筆電影"名稱(中+英)"到 Movie_Info-"各部電影名稱"
        "Movie_Name_Chinese": "%s" % (Chi_Name),
        "Movie_Name_English": "%s" % (Eng_Name)
    }
    doc_ref_Movie_Info_Name = db.collection("上映中電影").document("%s" % (Eng_Name))
    doc_ref_Movie_Info_Name.create(doc_Movie_Info_Name)

    upload(movie_url, Eng_Name)  # 取得其他相關的正在上映中的電影資訊


# ——————讀取Yahoo「本週新片」的電影,若其中有一部已經上映了則加入到上映中電影————————#
global how_many_movie
how_many_movie = 0  # 統計一共幾部電影
for i in range(1, 5, 1):  # 1到5每次加1
    res = requests.get('https://movies.yahoo.com.tw/movie_thisweek.html?page=' + str(i), headers=request_headers)
    soup = BeautifulSoup(res.text, 'lxml')
    info = soup.find_all('div', 'release_info')
    x = datetime.datetime.now()  # 取得當下時間

    for s in info:
        time_info = s.find('div', 'release_movie_time')
        time_processed = time_info.text.split(' ')[-1]
        year = int(time_processed.split('-')[0])
        month = int(time_processed.split('-')[1])
        day = int(time_processed.split('-')[2])
        if year < int(x.year) or month < int(x.month) or day <= int(x.day):
            ch = s.find('div', 'en')
            s2 = ch.find('a')
            get_movie_name(str(s2.get('href')), how_many_movie)  # 呼叫get_movie_name函數取得每一步電影的名稱


# ——————讀取Yahoo「上映中」的電影每一頁的每一部電影並取得其鏈接————————#
for i in range(1, 5, 1):  # 1到5每次加1
    res = requests.get('https://movies.yahoo.com.tw/movie_intheaters.html?page=' + str(i), headers=request_headers)
    soup = BeautifulSoup(res.text, 'lxml')
    ch = soup.find_all('div', 'en')
    for s in ch:
        s2 = s.find('a')
        get_movie_name(str(s2.get('href')), how_many_movie)  # 呼叫get_movie_name函數取得每一步電影的名稱


