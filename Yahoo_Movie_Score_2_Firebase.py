# ——————結合三個網站給電影一個分數————————#
# encoding: utf-8


# 導入爬蟲所需要的爬蟲的套件例如Http的request套件以及處理HTML的BeautifulSoup套件
import re
import requests
from bs4 import BeautifulSoup

# 導入爬蟲爛番茄的API
from rotten_tomatoes_client import RottenTomatoesClient

# 導入Google Cloud Client的函示庫
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types

# 設定環境變數GOOGLE安全認證json檔
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "GOOGLE NLP API KEY"

# 導入Firebase所需要的套件
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Firebase金鑰認證，驗證身分，只需要驗證一次就好了
cred = credentials.Certificate('GOOGLE FIREBASE API KEY')
firebase_admin.initialize_app(cred)
db = firestore.client()


# ——————將IMDb上面去將觀眾的留言用NLP做處理之後得到正負傾向————————#
def calculate_Rotten_Tomatoes_review_score(Rotten_Tomato_comment):
    global Tomatoes_start_score
    RTomatoes_comment_score_list = []  # 儲存每一則留言使用者的正負傾向的總分
    # 實例化LanguageService的客戶端
    client = language.LanguageServiceClient()
    for cnum in range(0, len(Rotten_Tomato_comment)):
        # 以下為將每一則留言丟進去分析情緒
        try:
            document = types.Document(content=Rotten_Tomato_comment[cnum], type=enums.Document.Type.PLAIN_TEXT)
            cloud_sentiment = client.analyze_sentiment(document=document)
            sentiment = cloud_sentiment.document_sentiment  # 整篇的情緒分析
            RTomatoes_comment_score_list.append(sentiment.score)
        except Exception:
            error = "Not Support!"

    Tomatoes_start_score = Tomatoes_start_score + sum(RTomatoes_comment_score_list) / len(RTomatoes_comment_score_list)


# ——————利用爬蟲程式到Rotten Tomatoes上面去將觀眾的留言都抓下來————————#
def get_Rotten_Tomatoes_review_data(movie_review_url):
    url = movie_review_url

    # 以下修改request的請求，避免出現Exceeded 30 redirects的問題
    request_headers = {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                      '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }
    r = requests.get(url, headers=request_headers)

    # 指定lxml為解析器，其他的解析器還有html.parser以及html5lib。其中速度最快的就是lxml解析器
    soup = BeautifulSoup(r.text, 'lxml')
    main_table = soup.find(id='reviews')
    every_comment = main_table.find_all('div', class_='user_review')  # 所有的留言部分
    every_start = main_table.find_all('span', class_='fl')  # 所有的星級評價，在爛番茄中一顆心表示一分，總共五顆星，1/2表示半顆心

    # 取出評論的頁數並利用迴圈將每一頁的留言都取出來
    page_info = main_table.find('span', class_='pageInfo')
    if page_info != None:
        page_num = int(page_info.get_text().split(' ')[3])
    else:
        page_num = 0

    if len(every_comment) != 0:
        # 儲存第一頁評論(已去除左右空格)與星級評分
        Rotten_Tomato_comment = []
        Rotten_Tomato_start = []
        for s in every_start:
            start_score = 0
            if s.get_text().replace(" ", "") != "":
                start_score += 0.5
            start_num = len(s.find_all('span', class_='glyphicon glyphicon-star'))  # 取出使用者給出星級評價
            start_score += start_num
            Rotten_Tomato_start.append(start_score)

        for t in every_comment:
            Rotten_Tomato_comment.append(t.get_text().strip())

        # 爬第二頁之後的評論
        if page_num > 1:
            for num in range(2, page_num + 1):
                old_url = movie_review_url.split('reviews')[0]
                new_url = old_url + '/reviews/?page=' + str(num) + '&type=user&sort='

                request_headers = {
                    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                                  '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
                }
                r = requests.get(new_url, headers=request_headers)
                soup = BeautifulSoup(r.text, 'lxml')
                main_table = soup.find(id='reviews')
                every_comment = main_table.find_all('div', class_='user_review')
                every_start = main_table.find_all('span', class_='fl')
                page_info = main_table.find('span', class_='pageInfo')
                if page_info != None:
                    page_num = int(page_info.get_text().split(' ')[3])
                else:
                    page_num = 0
                # 儲存第二頁到之後所有頁的星級評價
                for s in every_start:
                    start_score = 0
                    if s.get_text().replace(" ", "") != "":
                        start_score += 0.5
                    start_num = len(s.find_all('span', class_='glyphicon glyphicon-star'))  # 取出使用者給出星級評價
                    start_score += start_num
                    Rotten_Tomato_start.append(start_score)
                # 儲存第二頁到之後所有頁的評論(已去除左右空格)
                for t in every_comment:
                    Rotten_Tomato_comment.append(t.get_text().strip())

        calculate_Rotten_Tomatoes_review_score(Rotten_Tomato_comment)


# ——————得到一部電影在Rotten Tomatoes對應的評價網站——————#
def get_Rotten_Tomatoes_moviepage(moviename):
    search_result = RottenTomatoesClient.search(term=moviename, limit=10)['movies']  # 搜索RottenTomatoes中的電影名稱，並列舉出最多十個
    seach_result_len = len(search_result)  # 取得搜索紀錄的長度
    global movie_review_url  # 宣告一開始review的網址
    global Tomatoes_start_score, Tomatoes_start_people
    year_list = []  # 儲存年份的list
    url_list = []  # 儲存url的list
    if seach_result_len == 0:
        movie_review_url = ''
        Tomatoes_start_score = 0
        Tomatoes_start_people = 0
    elif seach_result_len == 1:
        if search_result[0]['name'].lower().strip().find(str(moviename).lower().strip()) != -1 or str(
                moviename).lower().strip().find(search_result[0]['name'].lower().strip()) != -1:
            movie_review_url = 'https://www.rottentomatoes.com' + search_result[0]['url']
            request_headers = {
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                              '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
            }
            r = requests.get(movie_review_url, headers=request_headers)

            soup = BeautifulSoup(r.text, 'lxml')
            main_table = soup.find('div', class_='audience-info hidden-xs superPageFontColor').find_all('div')

            # 獲得電影的星級評價與評價人數
            if len(main_table) >= 2:
                if main_table[0].text.split(':')[1].split('/')[0].replace('\n', '').replace(' ', '') != 'N':
                    Tomatoes_start_score = float(
                        main_table[0].text.split(':')[1].split('/')[0].replace('\n', '').replace(' ',
                                                                                                 '')) * 2  # 該部電影的星級評分
                    Tomatoes_start_people = int(
                        main_table[1].text.split(':')[1].replace('\n', '').replace(' ', '').replace(',',
                                                                                                    ''))  # 有幾個人給這部電影投票
                else:
                    Tomatoes_start_score = 0
                    Tomatoes_start_people = 0
            else:
                Tomatoes_start_score = 0
                Tomatoes_start_people = 0
            movie_review_url = movie_review_url + '/reviews/?type=user'
        else:
            movie_review_url = ''
            Tomatoes_start_score = 0
            Tomatoes_start_people = 0
    else:
        for each_search_result in search_result:
            if each_search_result['name'].lower().strip().find(str(moviename).lower().strip()) != -1 or str(
                    moviename).lower().strip().find(each_search_result['name'].lower().strip()) != -1:
                year_list.append(each_search_result['year'])
                url_list.append(each_search_result['url'])
        if len(url_list) == 0:
            movie_review_url = ''
            Tomatoes_start_score = 0
            Tomatoes_start_people = 0
        else:
            index_num = year_list.index(max(year_list))
            movie_review_url = 'https://www.rottentomatoes.com' + url_list[index_num]
            request_headers = {
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                              '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
            }
            r = requests.get(movie_review_url, headers=request_headers, allow_redirects=False)

            soup = BeautifulSoup(r.text, 'lxml')
            Tomatoes_start_score = 0
            Tomatoes_start_people = 0
            if soup.find('div', class_='audience-info hidden-xs superPageFontColor') != None:
                main_table = soup.find('div', class_='audience-info hidden-xs superPageFontColor').find_all('div')
                # 獲得電影的星級評價與評價人數
                if len(main_table) >= 2:
                    if main_table[0].text.split(':')[1].split('/')[0].replace('\n', '').replace(' ', '') != 'N':
                        Tomatoes_start_score = float(
                            main_table[0].text.split(':')[1].split('/')[0].replace('\n', '').replace(' ',
                                                                                                     '')) * 2  # 該部電影的星級評分
                        Tomatoes_start_people = int(
                            main_table[1].text.split(':')[1].replace('\n', '').replace(' ', '').replace(',',
                                                                                                        ''))  # 有幾個人給這部電影投票

            movie_review_url = movie_review_url + '/reviews/?type=user'
    #     print('Rotten Tomatoes:'+movie_review_url)

    if Tomatoes_start_score != 0 and movie_review_url != '':
        get_Rotten_Tomatoes_review_data(movie_review_url)


# ——————利用爬蟲程式到IMDb上面去將觀眾的留言都抓下來————————#
def get_IMDB_review_data(movie_review_url):
    if movie_review_url != '':  # 如果找得到IMDB上面的網址的話
        IMDb_comment = []  # 儲存文本評論
        IMDb_usefulcom = []  # 儲存多少使用者覺得有用

        # 爬蟲請求
        url = str(movie_review_url)
        #         print('IMDB:'+url)
        request_headers = {
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                          '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
        }
        r = requests.get(url, headers=request_headers)

        # 指定lxml為解析器，其他的解析器還有html.parser以及html5lib。其中速度最快的就是lxml解析器
        soup = BeautifulSoup(r.text, 'lxml')
        main_table = soup.find(id='main')
        every_comment = main_table.find_all('div',
                                            class_='text show-more__control')  # 所有留言文本
        useful_comment = main_table.find_all('div', class_='actions text-muted')  # 對留言的按讚或按噓

        if len(every_comment) != 0:

            for t in every_comment:  # 留言評分
                IMDb_comment.append(t.get_text().strip())

            for u in useful_comment:  # 對留言的按讚或按噓
                usful_com = u.get_text().replace('\n', '').strip()
                IMDb_usefulcom.append(usful_com.split(' ')[0] + ',' + usful_com.split(' ')[3])

            # IMDb的網站比較特別的地方就是要按下按鈕Load More載入更多
            if main_table.find('div', class_='load-more-data').get('data-key') != None:  # 判斷有多頁還是只有一頁
                data_key = main_table.find('div', class_='load-more-data')['data-key']  # 當Load到最後一頁的時候data_key會變成空字串
            else:  # 如果只有一頁的話
                data_key = ''
            data_ajaxurl = main_table.find('div', class_='load-more-data')['data-ajaxurl']

            # 利用while迴圈模擬按下Load More按鈕，一直到最後顯示全部留言
            while data_key != '':
                url_imdb2 = 'https://www.imdb.com' + data_ajaxurl + '&paginationKey=' + data_key
                request_headers = {
                    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                                  '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
                }
                r = requests.get(url_imdb2, headers=request_headers)

                soup = BeautifulSoup(r.text, 'lxml')
                every_comment = soup.find_all('div', class_='text show-more__control')  # 所有留言文本
                useful_comment = soup.find_all('div', class_='actions text-muted')  # 對留言的按讚或按噓

                for t in every_comment:  # 留言評分
                    IMDb_comment.append(t.get_text().strip())

                for u in useful_comment:  # 對留言的按讚或按噓
                    usful_com = u.get_text().replace('\n', '').strip()
                    IMDb_usefulcom.append(usful_com.split(' ')[0] + ',' + usful_com.split(' ')[3])

                key_table = soup.find('div', class_='load-more-data')
                if key_table != None:
                    data_key = key_table['data-key']  # 當Load到最後一頁的時候data_key會變成空字串
                else:
                    data_key = ''

            calculate_IMDB_review_score(IMDb_comment, IMDb_usefulcom)


# ——————透過影片的名稱找到IMDb對應的網站並找到其對應的評價網站——————#
def get_IMDB_moviepage(moviename):
    # 利用得到的電影名稱在IMDb上面搜索
    request_headers = {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                      '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }
    r = requests.get('https://www.imdb.com/find?ref_=nv_sr_fn&q=' + moviename + '&s=all', headers=request_headers)
    # print('https://www.imdb.com/find?ref_=nv_sr_fn&q='+moviename+'&s=all')
    soup = BeautifulSoup(r.text, 'lxml')
    search_result_odd = soup.find_all('tr', 'findResult odd')  # 查詢第奇數筆結果例如第1，第3，第5
    movie_url_list = [];  # 儲存搜索網頁的列表

    if len(search_result_odd) != 0:
        # 在搜索紀錄的第奇數筆裡面查看網址
        # ******這裡有個缺點就是搜索到的第一個不一定就是我們要找的電影*******#
        for index in search_result_odd:
            search_result = index.find('a')  # 找到a的標籤
            movie_url_list.append(search_result.get('href'))  # 將a標籤中的herf的網址指定為movie_url
        get_IMDB_moviepage_review(movie_url_list[0])  # 將搜索到的URL傳到下一個函式
    else:  # 搜索不到結果的時候
        movie_review_url = ''
        get_IMDB_review_data(movie_review_url)


# 找到影片留言評論的網址
def get_IMDB_moviepage_review(movieurl):
    movie_url = 'https://www.imdb.com' + str(movieurl)
    request_headers = {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                      '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }
    r = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(r.text, 'lxml')
    ch = soup.find_all('div', 'user-comments')

    # 獲得電影的星級評價與評價人數
    global IMDb_start_score, IMDb_start_people
    if soup.find('div', class_='imdbRating') != None:
        if soup.find('div', class_='imdbRating').find('span', itemprop="ratingValue") != None:
            IMDb_start_score = float(
                soup.find('div', class_='imdbRating').find('span', itemprop="ratingValue").text)  # 該部電影的星級評分
            IMDb_start_people = int(
                soup.find('div', class_='imdbRating').find('span', class_='small').text.replace(',', ''))  # 有幾個人給這部電影投票
        else:
            IMDb_start_score = 0
            IMDb_start_people = 0
    else:
        IMDb_start_score = 0
        IMDb_start_people = 0

    if len(ch) != 0:
        for index in ch:
            index2 = index.find_all('a')  # 找到所有帶網址的標籤
            see_all = index2[-1]  # 找到see all user reviews對應的標籤
            see_all_url = see_all.get('href')  # 找到see all user reviews對應的標籤內的url網址
        movie_review_url = see_all_url.split('?')[0] + '?spoiler=hide&sort=helpfulnessScore&dir=desc&ratingFilter=0'
        movie_review_url = 'https://www.imdb.com' + movie_review_url
        get_IMDB_review_data(movie_review_url)
    else:
        movie_review_url = ''
        get_IMDB_review_data(movie_review_url)


# ——————透過電影名稱搜索IMDB與爛番茄上面的影評————————#
def search_movie_website(eng_name):
    get_IMDB_moviepage(eng_name)  # 獲得IMDb上面該電影的網址
    get_Rotten_Tomatoes_moviepage(eng_name)  # 獲得Rotten Tomatoes上面該電影的網址

    global Yahoo_total_people, IMDb_start_people, Tomatoes_start_people, Yahoo_total_score, IMDb_start_score, Tomatoes_start_score
    # 計算最後的總分資料傳到Firebase上面
    total_people = int(Yahoo_total_people + IMDb_start_people + Tomatoes_start_people)
    total_score = float(Yahoo_total_people / total_people * Yahoo_total_score) + float(
        IMDb_start_people / total_people * IMDb_start_score) + float(
        Tomatoes_start_people / total_people * Tomatoes_start_score)

    # 以下將「正在上映電影的評分」更新到Firebase
    doc_Movie_Info_Score = {  # 傳送每一筆電影評分到 「上映中電影」
        "Movie_Score": "%s" % (total_score)
    }

    print(eng_name)
    print(total_score)
    doc_ref_Movie_Info_Score = db.collection("上映中電影").document("%s" % (eng_name))
    doc_ref_Movie_Info_Score.update(doc_Movie_Info_Score)


# ——————利用爬蟲程式到Yahoo電影上面去將評分與投票人數都抓下來————————#
def get_Yahoo_movie_score(movie_url, movie_name):
    global Yahoo_total_score, Yahoo_total_people
    request_headers = {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                      '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }
    res = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    ch = soup.find('div', 'evaluate_txt starwithnum')
    Yahoo_total_score = (float(ch.find('div', 'score_num count').text) * 2)  # 紀錄下
    Yahoo_total_people = int(ch.find('div', 'starbox2').find('span').text.split('共')[1].split('人')[0])
    search_movie_website(movie_name)  # 透過電影名稱搜索IMDB與爛番茄上面的影評資料


# ——————取得上映中每一部電影的電影名稱並上傳到Firebase————————#
def get_movie_name(movie_url):
    request_headers = {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                      '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }
    res = requests.get(movie_url, headers=request_headers)
    soup = BeautifulSoup(res.text, 'lxml')
    ch = soup.find_all('div', 'movie_intro_info_r')

    for s in ch:
        s2 = s.find('h1')  # 取出中文
        s3 = s.find('h3')  # 取出英文

    get_Yahoo_movie_score(movie_url, str(s3.text))  # 取得Yahoo的電影評價


# ——————將IMDb上面去將觀眾的留言用NLP做處理之後得到正負傾向————————#
def calculate_IMDB_review_score(IMDb_comment, IMDb_usefulcom):
    IMDb_comment_score_list = []  # 儲存每一則留言使用者的正負傾向的總分
    # 實例化LanguageService的客戶端
    client = language.LanguageServiceClient()
    global IMDb_start_score
    for cnum in range(0, len(IMDb_comment)):
        # 以下為將每一則留言丟進去分析情緒
        try:
            document = types.Document(content=IMDb_comment[cnum], type=enums.Document.Type.PLAIN_TEXT)
            cloud_sentiment = client.analyze_sentiment(document=document)
            sentiment = cloud_sentiment.document_sentiment  # 整篇的情緒分析

            # 以下取出每一則留言裡面有多少人覺得有用
            useful_comment = IMDb_usefulcom[cnum].split(',')[0]
            total_comment = IMDb_usefulcom[cnum].split(',')[1]

            # 以下將每一則留言正負傾向乘上【1+（覺得有用的人/總人）】
            if int(total_comment) == 0:
                IMDb_comment_score_list.append(sentiment.score)
            else:
                IMDb_comment_score_list.append(sentiment.score * (1 + int(useful_comment) / int(total_comment)))
        except Exception:
            error = "Not Support!"

    IMDb_start_score = IMDb_start_score + sum(IMDb_comment_score_list) / len(IMDb_comment_score_list)


# ——————讀取Yahoo「上映中」的電影每一頁的每一部電影並取得其鏈接————————#
for i in range(1, 2, 1):  # 1到10每次加1
    request_headers = {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36' +
                      '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }
    res = requests.get('https://movies.yahoo.com.tw/movie_intheaters.html?page=' + str(i), headers=request_headers)
    soup = BeautifulSoup(res.text, 'lxml')
    ch = soup.find_all('div', 'en')
    for s in ch:
        s2 = s.find('a')
        get_movie_name(str(s2.get('href')))  # 呼叫get_movie_name函數取得每一部電影的名稱
        print('Yahoo星級數：' + str(Yahoo_total_score) + ',' + 'Yahoo星級人數：' + str(Yahoo_total_people)
              + ',' + 'IMDB星級數：' + str(IMDb_start_score) + ',' + 'IMDB星級人數：' + str(IMDb_start_people) + ','
              + 'Rotten星級數：' + str(Tomatoes_start_score) + ',' + 'Rotten星級人數：' + str(Tomatoes_start_people))
