#以下為LineBot需要的套件
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    TemplateSendMessage, CarouselTemplate, CarouselColumn,
    PostbackTemplateAction,URITemplateAction,LocationMessage,
    FollowEvent,ButtonsTemplate,PostbackEvent
)

#以下為推播系統後台執行
from apscheduler.schedulers.background import BackgroundScheduler

#以下為Google Firebase儲存資料所需要的套件
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

#以下為使用Google Map API所需要的套件
import googlemaps

# 導入Google Cloud Client的函示庫
import google.cloud

# 導入時間的套件
import datetime,re,random,pytz
import collections

app = Flask(__name__)

line_bot_api = LineBotApi('LINE BOT API KEY')
handler = WebhookHandler('LINE BOT HANDLER')

#以下為使用者使用Google提供的Firebase所需要的金鑰
cred = credentials.Certificate('GOOGLE FIREBASE API KEY')
firebase_admin.initialize_app(cred)
# 宣告Firebase的客戶端Client
db = firestore.client()
# 宣告我們的時區
tz = pytz.timezone('Asia/Taipei')

#***隨機五部上映中電影給使用者***
def get_movie_releasenow(user_token):
    users_ref = db.collection("隨機推薦電影清單").document('上映中')
    docs = users_ref.get()
    movie_name = []  # 存上映中電影名稱
    for doc in docs.to_dict():
        movie_name.append(str(docs.to_dict().get(doc).strip()))

    image_url = []           # 圖片網址
    movie_name_Chinese = []  # 電影中文名稱
    movie_name_English = []  # 電影英文名稱
    movie_type = []          # 電影類型
    trailer_url = []         # 預告片網址
    age_level = []           # 電影分級

    line_bot_api.push_message(
        user_token, TextSendMessage('正在為您尋找上映中評分最高且最適合您的電影...')
    )

    for lis in range(0,8,1):
        users_ref = db.collection("上映中電影").document("%s" % (movie_name[lis]))
        doc = users_ref.get()
        if 'Movie_Name_Chinese' in doc.to_dict():
            movie_name_Chinese.append(doc.to_dict()['Movie_Name_Chinese'])
        else:
            movie_name_Chinese.append('')

        if 'Movie_Name_English' in doc.to_dict():
            movie_name_English.append(doc.to_dict()['Movie_Name_English'])
        else:
            movie_name_English.append('')

        if 'Movie_ImageURL' in doc.to_dict():
            image_url.append(doc.to_dict()['Movie_ImageURL'])
        else:
            image_url.append('')

        if 'Movie_PreviewURL' in doc.to_dict():
            trailer_url.append(doc.to_dict()['Movie_PreviewURL'])
        else:
            trailer_url.append('')

        if 'Movie_Type' in doc.to_dict():
            movie_type.append(doc.to_dict()['Movie_Type'])
        else:
            movie_type.append('')

        if 'Movie_AgeLimit' in doc.to_dict():
            age_level.append(doc.to_dict()['Movie_AgeLimit'])
        else:
            age_level.append('0+')

    # 宣告儲存橫向捲軸的list
    column_list = []
    for pnum in range(0,8,1):
        if trailer_url[pnum] != '':
            URLweb = trailer_url[pnum]
        else:
            URLweb = 'https://www.youtube.com/results?search_query='+movie_name_Chinese[pnum]+'預告'

        carouselcolumn = CarouselColumn(
            thumbnail_image_url='%s' % (image_url[pnum]),  # 電影的圖片
            title='電影名稱：%s' % (movie_name_Chinese[pnum]),  # 電影的名字
            text='電影類型：'+movie_type[pnum]+'\n'+'分級限制：' + age_level[pnum],  # 電影的類型
            actions=[
                PostbackTemplateAction(
                    label='我想看這部',
                    text='我想看'+'\n'+movie_name_Chinese[pnum],
                    data='我想看'+'\n'+movie_name_Chinese[pnum]
                ),
                URITemplateAction(
                    label='觀看預告',
                    uri='%s' % (URLweb)
                )
            ]
        )
        column_list.append(carouselcolumn)

        Carousel_template = CarouselTemplate(
            columns=column_list,
            image_aspect_ratio="square",  # 圖片形狀，一共兩個參數。square指圖片1:1，rectangle指圖片1.5:1
            image_size="contain"  # 圖片size大小設定，一共兩個參數。cover指圖片充滿畫面，contain指縮小圖片塞到畫面
        )
    line_bot_api.push_message(user_token,TemplateSendMessage(alt_text="為您推薦上映中的電影", template=Carousel_template))  # 將影城的圖片等資訊傳送給使用者)

#***隨機給使用者推薦五部即將上映的電影***
def get_movie_comingsoon(user_token):
    users_ref = db.collection("隨機推薦電影清單").document('即將上映')
    docs = users_ref.get()
    x = []
    movie_num = []
    movie_name = []
    user_ref = db.collection("使用者電影喜好調查").document(user_token)
    docs = user_ref.get()
    user_ref2 = db.collection("即將上映電影")
    do = user_ref2.get()
    age = docs.to_dict()['年齡']
    z = []
    z.append(docs.to_dict()['不能接受的電影類型'])
    z = z[0].split(",")
    moviecom = []
    moviecomage = []
    moviecomtype = []
    for doc in do:
        moviecom.append(doc.id)
        moviecomage.append(doc.to_dict()['Movie_AgeLimit'].replace("+", ""))
        moviecomtype.append(doc.to_dict()['Movie_Type'])
    moviecomin = []
    moviecomintype = []
    final = []
    sum = 0
    for j in range(0, len(moviecomage), 1):
        if int(age) >= int(moviecomage[j]):
            moviecomin.append(moviecom[j])
            moviecomintype.append(moviecomtype[j])
        else:
            continue
    print(len(moviecomintype))
    for f in range(0, len(moviecomintype), 1):
        for h in range(0, len(z), 1):
            if z[h].replace("片", "") in moviecomintype[f]:
                final.append(moviecomin[f])
                break
            else:
                continue
    for k in range(0, len(final)):
        moviecomin.remove(final[k])
    movie_name_R = []
    movie_num_random = random.sample(range(0, len(moviecomin)), 5)
    for num in movie_num_random:
        movie_name_R.append(moviecomin[num])
    image_url = []           # 圖片網址
    movie_name_Chinese = []  # 電影中文名稱
    movie_name_English = []  # 電影英文名稱
    movie_type = []          # 電影類型
    trailer_url = []         # 預告片網址
    age_level = []           # 電影分級
    movie_time = []          # 電影上映日期

    line_bot_api.push_message(
        user_token, TextSendMessage('正在為您尋找即將上映的電影...')
    )

    for lis in range(0, len(movie_name_R)):
        users_ref = db.collection("即將上映電影").document("%s" % (movie_name_R[lis]))
        doc = users_ref.get()

        if 'Movie_Name_Chinese' in doc.to_dict():
            movie_name_Chinese.append(doc.to_dict()['Movie_Name_Chinese'])
        else:
            movie_name_Chinese.append('')

        if 'Movie_Name_English' in doc.to_dict():
            movie_name_English.append(doc.to_dict()['Movie_Name_English'])
        else:
            movie_name_English.append('')

        if 'Movie_ImageURL' in doc.to_dict():
            image_url.append(doc.to_dict()['Movie_ImageURL'])
        else:
            image_url.append('')

        if 'Movie_PreviewURL' in doc.to_dict():
            trailer_url.append(doc.to_dict()['Movie_PreviewURL'])
        else:
            trailer_url.append('')

        if 'Movie_Type' in doc.to_dict():
            movie_type.append(doc.to_dict()['Movie_Type'])
        else:
            movie_type.append('')

        if 'Movie_AgeLimit' in doc.to_dict():
            age_level.append(doc.to_dict()['Movie_AgeLimit'])
        else:
            age_level.append('')

        if 'Movie_ReleaseTime' in doc.to_dict():
            movie_time.append(doc.to_dict()['Movie_ReleaseTime'])
        else:
            movie_time.append('')

    print(image_url)
    print(movie_name_Chinese)
    print(trailer_url)
    print(age_level)
    print(movie_time)

    # 宣告儲存橫向捲軸的list
    column_list = []
    for pnum in range(0, 4, 1):
        if trailer_url[pnum] != '':
            URLweb = trailer_url[pnum]
        else:
            URLweb = 'https://www.youtube.com/results?search_query=' + movie_name_Chinese[pnum] + '預告'

        carouselcolumn = CarouselColumn(
            thumbnail_image_url='%s' % (image_url[pnum]),  # 電影的圖片
            title='電影名稱：%s' % (movie_name_Chinese[pnum]),  # 電影的名字
            text='電影類型：' + movie_type[pnum]+'\n'+'分級限制：' + age_level[pnum]+'\n'+'上映時間：' + movie_time[pnum],  # 電影的類型
            actions=[
                PostbackTemplateAction(
                    label='預約看這部',
                    text='我想預約' + '\n' + movie_name_Chinese[pnum],
                    data='我想預約' + '\n' + movie_name_Chinese[pnum]
                ),
                URITemplateAction(
                    label='觀看預告',
                    uri='%s' % (URLweb)
                )
            ]
        )
        column_list.append(carouselcolumn)

        Carousel_template = CarouselTemplate(
            columns=column_list,
            image_aspect_ratio="square",  # 圖片形狀，一共兩個參數。square指圖片1:1，rectangle指圖片1.5:1
            image_size="contain"  # 圖片size大小設定，一共兩個參數。cover指圖片充滿畫面，contain指縮小圖片塞到畫面
        )
    line_bot_api.push_message(user_token, TemplateSendMessage(alt_text="為您推薦即將上映的電影",
                                                                  template=Carousel_template))  # 將影城的圖片等資訊傳送給使用者)

#***發送推播給使用者推薦電影***
def push_to_user():
    #list = ['Ue723effb9d5a2f9a1d36b0d25ba78aec','U640d7c18fa27781408a9626e26208f2c']
    list = ['U0eec8249b1cca09cbbe0cdbb0eef801f']
    users_ref = db.collection("隨機推薦電影清單").document('即將上映')
    docs = users_ref.get()
    x = []
    movie_num = []
    movie_name = []
    user_ref = db.collection("使用者電影喜好調查").document(list[0])
    docs = user_ref.get()
    user_ref2 = db.collection("即將上映電影")
    do = user_ref2.get()
    age = docs.to_dict()['年齡']
    z = []
    z.append(docs.to_dict()['不能接受的電影類型'])
    z = z[0].split(",")
    moviecom = []
    moviecomage = []
    moviecomtype = []
    for doc in do:
        moviecom.append(doc.id)
        moviecomage.append(doc.to_dict()['Movie_AgeLimit'].replace("+", ""))
        moviecomtype.append(doc.to_dict()['Movie_Type'])
    moviecomin = []
    moviecomintype = []
    final = []
    sum = 0
    for j in range(0, len(moviecomage), 1):
        if int(age) >= int(moviecomage[j]):
            moviecomin.append(moviecom[j])
            moviecomintype.append(moviecomtype[j])
        else:
            continue
    print(len(moviecomintype))
    for f in range(0, len(moviecomintype), 1):
        for h in range(0, len(z), 1):
            if z[h].replace("片", "") in moviecomintype[f]:
                final.append(moviecomin[f])
                break
            else:
                continue
    for k in range(0, len(final)):
        moviecomin.remove(final[k])
    movie_name_R = []
    movie_num_random = random.sample(range(0, len(moviecomin)), 5)
    for num in movie_num_random:
        movie_name_R.append(moviecomin[num])

    image_url = []  # 圖片網址
    movie_name_Chinese = []  # 電影中文名稱
    movie_name_English = []  # 電影英文名稱
    movie_type = []  # 電影類型
    trailer_url = []  # 預告片網址
    age_level = []  # 電影分級
    movie_time = []  # 電影上映日期

    for lis in range(0, len(movie_name_R)):
        users_ref = db.collection("即將上映電影").document("%s" % (movie_name_R[lis]))
        doc = users_ref.get()

        if 'Movie_Name_Chinese' in doc.to_dict():
            movie_name_Chinese.append(doc.to_dict()['Movie_Name_Chinese'])
        else:
            movie_name_Chinese.append('')

        if 'Movie_Name_English' in doc.to_dict():
            movie_name_English.append(doc.to_dict()['Movie_Name_English'])
        else:
            movie_name_English.append('')

        if 'Movie_ImageURL' in doc.to_dict():
            image_url.append(doc.to_dict()['Movie_ImageURL'])
        else:
            image_url.append('')

        if 'Movie_PreviewURL' in doc.to_dict():
            trailer_url.append(doc.to_dict()['Movie_PreviewURL'])
        else:
            trailer_url.append('')

        if 'Movie_Type' in doc.to_dict():
            movie_type.append(doc.to_dict()['Movie_Type'])
        else:
            movie_type.append('')

        if 'Movie_AgeLimit' in doc.to_dict():
            age_level.append(doc.to_dict()['Movie_AgeLimit'])
        else:
            age_level.append('')

        if 'Movie_ReleaseTime' in doc.to_dict():
            movie_time.append(doc.to_dict()['Movie_ReleaseTime'])
        else:
            movie_time.append('')

    print(image_url)
    print(movie_name_Chinese)
    print(trailer_url)
    print(age_level)
    print(movie_time)

    # 宣告儲存橫向捲軸的list
    column_list = []
    for pnum in range(0, 4, 1):
        if trailer_url[pnum] != '':
            URLweb = trailer_url[pnum]
        else:
            URLweb = 'https://www.youtube.com/results?search_query=' + movie_name_Chinese[pnum] + '預告'

        carouselcolumn = CarouselColumn(
            thumbnail_image_url='%s' % (image_url[pnum]),  # 電影的圖片
            title='電影名稱：%s' % (movie_name_Chinese[pnum]),  # 電影的名字
            text='電影類型：' + movie_type[pnum] + '\n' + '分級限制：' + age_level[pnum] + '\n' + '上映時間：' + movie_time[pnum],
            # 電影的類型
            actions=[
                PostbackTemplateAction(
                    label='預約看這部',
                    text='我想預約' + '\n' + movie_name_Chinese[pnum],
                    data='我想預約' + '\n' + movie_name_Chinese[pnum]
                ),
                URITemplateAction(
                    label='觀看預告',
                    uri='%s' % (URLweb)
                )
            ]
        )
        column_list.append(carouselcolumn)

        Carousel_template = CarouselTemplate(
            columns=column_list,
            image_aspect_ratio="square",  # 圖片形狀，一共兩個參數。square指圖片1:1，rectangle指圖片1.5:1
            image_size="contain"  # 圖片size大小設定，一共兩個參數。cover指圖片充滿畫面，contain指縮小圖片塞到畫面
        )
    for li in list:
        line_bot_api.push_message(li, TemplateSendMessage(alt_text="推播訊息："+'\n'+"為您推薦即將上映的電影",
                                                              template=Carousel_template))  # 將影城的圖片等資訊傳送給使用者)

#***LCS最長公共子序列函式***
def lcs(s1, s2):
    tokens1, tokens2 = list(s1), list(s2)
    cache = collections.defaultdict(dict)
    for i in range(-1, len(tokens1)):
        for j in range(-1, len(tokens2)):
            if i == -1 or j == -1:
                cache[i][j] = 0
            else:
                if tokens1[i] == tokens2[j]:
                    cache[i][j] = cache[i - 1][j - 1] + 1
                else:
                    cache[i][j] = max(cache[i - 1][j], cache[i][j - 1])
    return cache[len(tokens1) - 1][len(tokens2) - 1]

#***按照使用者搜索紀錄發送上映中電影給使用者***#
def keyword_search_releasing(user_id,user_text):
    users_refs = db.collection('隨機推薦電影清單').document('上映中(中文)')
    score_rank = []  # 建立一個暫存相似度分數，以便之後從小到大排序
    relative_list = []  # 創建計算LCS similarities的list
    name_list = []  # 創建LCS similarities計算後數值大於0的電影名稱的list
    similar = 0 #定義相似度初始值為0
    try:
        docs = users_refs.get()
        for doc in docs.to_dict():
            mov_name_ch = str(docs.to_dict().get(doc).strip()).split('$%$')[0].strip()
            mov_name_en = str(docs.to_dict().get(doc).strip()).split('$%$')[1].strip()
            max_len = max(len(mov_name_ch),len(user_text)) # 最大字串長度
            lcs_len = lcs(str(user_text), mov_name_ch)  # LCS得到的最大字串長度
            similar = float(lcs_len / max_len)  # 相似度

            if len(relative_list) < 5 and similar > 0:
                if similar in relative_list:
                    similar = similar + (random.randint(0, 1000) * 0.000001)
                relative_list.append(similar)
                name_list.append(mov_name_en)

            elif len(relative_list) == 5 and similar > 0:
                if similar > min(relative_list):
                    if similar in relative_list:
                        similar = similar + (random.randint(0, 1000) * 0.000001)
                    name_list[relative_list.index(min(relative_list))] = mov_name_en
                    relative_list[relative_list.index(min(relative_list))] = similar
        # print(name_list) # 測試BUG
        # print(relative_list) # 測試BUG
        if len(relative_list) == 0:
            line_bot_api.push_message(
                user_id, TextSendMessage('親' + '\n' + '很抱歉我們找不到與您下的關鍵詞相關的電影')
            )
            # keyword_search_coming(user_id,user_text) #若在上映中沒有使用者想看那部則跳到即將上映
        else:
            score_rank = relative_list.copy()
            print(score_rank)  # 測試BUG
            score_rank.sort(reverse=True)
            print(score_rank)  # 測試BUG

            image_url = []  # 圖片網址
            movie_name_Chinese = []  # 電影中文名稱
            movie_name_English = []  # 電影英文名稱
            movie_type = []  # 電影類型
            movie_score = []  # 電影分數
            trailer_url = []  # 預告片網址
            age_level = []  # 電影分級

            for score_b in score_rank:
                #print(name_list[relative_list.index(score_b)])
                users_ref = db.collection("上映中電影").document("%s" % (name_list[relative_list.index(score_b)]))
                doc = users_ref.get()

                if 'Movie_Name_Chinese' in doc.to_dict():
                    movie_name_Chinese.append(doc.to_dict()['Movie_Name_Chinese'])
                else:
                    movie_name_Chinese.append('')

                if 'Movie_Name_English' in doc.to_dict():
                    movie_name_English.append(doc.to_dict()['Movie_Name_English'])
                else:
                    movie_name_English.append('')

                if 'Movie_ImageURL' in doc.to_dict():
                    image_url.append(doc.to_dict()['Movie_ImageURL'])
                else:
                    image_url.append('')

                if 'Movie_PreviewURL' in doc.to_dict():
                    trailer_url.append(doc.to_dict()['Movie_PreviewURL'])
                else:
                    trailer_url.append('')

                if 'Movie_Type' in doc.to_dict():
                    movie_type.append(doc.to_dict()['Movie_Type'])
                else:
                    movie_type.append('')

                # if 'Movie_Score' in doc.to_dict():
                #     movie_score.append(doc.to_dict()['Movie_Score'])
                # else:
                #     movie_score.append('')

                if 'Movie_AgeLimit' in doc.to_dict():
                    age_level.append(doc.to_dict()['Movie_AgeLimit'])
                else:
                    age_level.append('')

            # 宣告儲存橫向捲軸的list
            column_list = []
            lenth = len(relative_list)

            for pnum in range(0,lenth):
                print(movie_name_Chinese[pnum])

                if trailer_url[pnum] != '':
                    URLweb = trailer_url[pnum]
                else:
                    URLweb = 'https://www.youtube.com/results?search_query=' + movie_name_Chinese[pnum] + '預告'

                carouselcolumn = CarouselColumn(
                    thumbnail_image_url='%s' % (image_url[pnum]),  # 電影的圖片
                    title='電影名稱：%s' % (movie_name_Chinese[pnum]),  # 電影的名字
                    text='電影類型：' + movie_type[pnum] + '\n' + '分級限制：' + age_level[pnum],  # 電影的類型
                    actions=[
                        PostbackTemplateAction(
                            label='我想看這部',
                            text='我想看' + '\n' + movie_name_Chinese[pnum],
                            data='我想看' + '\n' + movie_name_Chinese[pnum]
                        ),
                        URITemplateAction(
                            label='觀看預告',
                            uri='%s' % (URLweb)
                        )
                    ]
                )
                column_list.append(carouselcolumn)
                print('OK')

            Carousel_template = CarouselTemplate(
                columns=column_list,
                image_aspect_ratio="square",  # 圖片形狀，一共兩個參數。square指圖片1:1，rectangle指圖片1.5:1
                image_size="contain"  # 圖片size大小設定，一共兩個參數。cover指圖片充滿畫面，contain指縮小圖片塞到畫面
            )
            line_bot_api.push_message(user_id, TemplateSendMessage(alt_text="與您搜索的關鍵詞最接近的電影",
                                                                      template=Carousel_template))  # 將影城的圖片等資訊傳送給使用者)

    except Exception:
        print('error in getting movie time')
        line_bot_api.push_message(
            user_id, TextSendMessage('親' + '\n' + '很抱歉我們找不到與您下的關鍵詞相關的電影')
        )

#***按照使用者搜索紀錄發送即將電影給使用者***#
def keyword_search_coming(user_id,user_text):
    users_refs = db.collection('隨機推薦電影清單').document('即將上映(中文)')
    score_rank = []  # 建立一個暫存相似度分數，以便之後從小到大排序
    relative_list = []  # 創建計算LCS similarities的list
    name_list = []  # 創建LCS similarities計算後數值大於0的電影名稱的list
    try:
        docs = users_refs.get()
        for doc in docs.to_dict():
            mov_name_ch = str(docs.to_dict().get(doc).strip()).split('$%$')[0].strip()
            mov_name_en = str(docs.to_dict().get(doc).strip()).split('$%$')[1].strip()
            max_len = max(len(mov_name_ch), len(user_text))  # 最大字串長度
            # max_len = (len(mov_name_ch) + len(user_text)) / 2
            lcs_len = lcs(str(user_text), mov_name_ch)  # LCS得到的最大字串長度
            similar = float(lcs_len / max_len)  # 相似度

            if len(relative_list) < 5 and similar > 0:
                if similar in relative_list:
                    similar = similar + (random.randint(0, 1000) * 0.000001)
                relative_list.append(similar)
                name_list.append(mov_name_en)

            elif len(relative_list) == 5 and similar > 0:
                if similar > min(relative_list):
                    if similar in relative_list:
                        similar = similar + (random.randint(0, 1000) * 0.000001)
                    name_list[relative_list.index(min(relative_list))] = mov_name_en
                    relative_list[relative_list.index(min(relative_list))] = similar
        # print(name_list) # 測試BUG
        # print(relative_list) # 測試BUG
        if len(relative_list) == 0:
            line_bot_api.push_message(
                user_id, TextSendMessage('親' + '\n' + '很抱歉我們找不到與您下的關鍵詞相關的電影')
            )
        else:
            score_rank = relative_list.copy()
            # print(score_rank)  # 測試BUG
            score_rank.sort(reverse=True)
            # print(score_rank)  # 測試BUG

            image_url = []  # 圖片網址
            movie_name_Chinese = []  # 電影中文名稱
            movie_name_English = []  # 電影英文名稱
            movie_type = []  # 電影類型
            trailer_url = []  # 預告片網址
            age_level = []  # 電影分級
            movie_time = []  # 電影上映日期

            for score_b in score_rank:
                users_ref = db.collection("即將上映電影").document("%s" % (name_list[relative_list.index(score_b)]))
                doc = users_ref.get()

                if 'Movie_Name_Chinese' in doc.to_dict():
                    movie_name_Chinese.append(doc.to_dict()['Movie_Name_Chinese'])
                else:
                    movie_name_Chinese.append('')

                if 'Movie_Name_English' in doc.to_dict():
                    movie_name_English.append(doc.to_dict()['Movie_Name_English'])
                else:
                    movie_name_English.append('')

                if 'Movie_ImageURL' in doc.to_dict():
                    image_url.append(doc.to_dict()['Movie_ImageURL'])
                else:
                    image_url.append('')

                if 'Movie_PreviewURL' in doc.to_dict():
                    trailer_url.append(doc.to_dict()['Movie_PreviewURL'])
                else:
                    trailer_url.append('')

                if 'Movie_Type' in doc.to_dict():
                    movie_type.append(doc.to_dict()['Movie_Type'])
                else:
                    movie_type.append('')

                if 'Movie_AgeLimit' in doc.to_dict():
                    age_level.append(doc.to_dict()['Movie_AgeLimit'])
                else:
                    age_level.append('')

                if 'Movie_ReleaseTime' in doc.to_dict():
                    movie_time.append(doc.to_dict()['Movie_ReleaseTime'])
                else:
                    movie_time.append('')



            # 宣告儲存橫向捲軸的list
            column_list = []
            lenth = len(relative_list)
            for pnum in range(0, lenth):
                if trailer_url[pnum] != '':
                    URLweb = trailer_url[pnum]
                else:
                    URLweb = 'https://www.youtube.com/results?search_query=' + movie_name_Chinese[pnum] + '預告'

                carouselcolumn = CarouselColumn(
                    thumbnail_image_url='%s' % (image_url[pnum]),  # 電影的圖片
                    title='電影名稱：%s' % (movie_name_Chinese[pnum]),  # 電影的名字
                    text='電影類型：' + movie_type[pnum]+'\n'+'分級限制：' + age_level[pnum]+'\n'+'上映時間：' + movie_time[pnum],  # 電影的類型
                    actions=[
                        PostbackTemplateAction(
                            label='預約看這部',
                            text='我想預約' + '\n' + movie_name_Chinese[pnum],
                            data='我想預約' + '\n' + movie_name_Chinese[pnum]
                        ),
                        URITemplateAction(
                            label='觀看預告',
                            uri='%s' % (URLweb)
                        )
                    ]
                )
                column_list.append(carouselcolumn)

            Carousel_template = CarouselTemplate(
                columns=column_list,
                image_aspect_ratio="square",  # 圖片形狀，一共兩個參數。square指圖片1:1，rectangle指圖片1.5:1
                image_size="contain"  # 圖片size大小設定，一共兩個參數。cover指圖片充滿畫面，contain指縮小圖片塞到畫面
            )
            line_bot_api.push_message(user_id, TemplateSendMessage(alt_text="為您推薦即將上映的電影",template=Carousel_template))  # 將影城的圖片等資訊傳送給使用者

    except Exception:
        print('error in getting movie time')
        line_bot_api.push_message(
            user_id, TextSendMessage('親' + '\n' + '很抱歉我們找不到與您下的關鍵詞相關的電影')
        )

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(800)

    return 'OK'

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):

    #獲得經緯度
    lan = event.message.latitude
    lon = event.message.longitude
    #宣告儲存橫向捲軸的list
    column_list = []
    #宣告Firebase的客戶端Client
    db = firestore.client()

    #******Google Map API使用*******#
    # Google Map API需要的API KEY
    gmaps = googlemaps.Client(key='AIzaSyAuBskIN3x5-067Ex5n3ZyftqMnjmZR_ik')

    line_bot_api.push_message(
        event.source.user_id, TextSendMessage('正在為您加載附近電影院資訊請稍等片刻...')
    )

    # 利用places_nearby的方法搜索尋找附近的電影院 按照距離從近到遠排序
    nearby_search = gmaps.places_nearby(
        location=(lan, lon),  # 目前的位置必須是經緯度
        keyword='影城',  # 搜尋中關鍵字
        language='zh-TW',  # 回傳回來的語言
        type='movie_theater',  # 種類是電影院
        rank_by='distance')  # rankby表示搜索到的影城按照distance距離從近到遠排序

    #****從資料庫抓使用者剛剛點了哪一部電影然後搜尋時刻表****#
    user_id = event.source.user_id
    x = datetime.datetime.now(tz)  # 取得當下時間
    time_now = str(x.year) + ' ' + str(x.month) + ' ' + str(x.day) + ' ' + ' ' + str(x.date().isoweekday()) + ' ' + str(
        x.hour) + ' ' + str(x.minute) + ' ' + str(x.second)
    theater_name = [] #宣告使用者想看的電影的影城名稱
    movie_time_list = [] #宣告使用者想看的電影的影城時間

    #****取得使用者之前的想要看什麼電影的資訊****#
    users_ref = db.collection("使用者想看電影紀錄").document(user_id)
    doc = users_ref.get()
    user_movie = doc.to_dict()['最近一筆資料']
    #print(user_movie)

    #到Firebase找到使用者想看的電影的時刻表
    users_refs = db.collection("電影時刻表").document(str(user_movie).strip())
    try:
        docs = users_refs.get()
        for doc in docs.to_dict():
            theater_name.append(str(doc).split('{')[0])
            movie_time_list.append(str(docs.to_dict().get(doc).strip()))
    except Exception:
        print('error in getting movie time')

    # print(theater_name) #測試BUG
    # print(movie_time_list) #測試BUG

    # 找到五個最近影城的名稱，地理位置以及Place ID
    nearby_place = nearby_search['results']
    place_lenth = len(nearby_place)

    five_movie_place_time = []  # 紀錄(最多)五個距離使用者最近又有電影上映的影城的時刻表
    movie_time_times = -1       # 紀錄影城的時刻表是第幾個裡面的
    if len(theater_name) == 0:
        place_lenth = 0
    else:
        if place_lenth > 18:
            place_lenth = 18
        for pnum in range(0, place_lenth):
            bool_inCHN = False
            place_ID = nearby_place[pnum]['place_id']        # 影城的id，需要靠這個得到更具體的資訊
            place_NAME = nearby_place[pnum]['name']          # 影城的名字資訊

            if len(five_movie_place_time) == 10:
                break

            #若該電影院的名稱出現在movie_name的list中
            if str(place_NAME) in theater_name:
                #******將附近的電影院資訊與有該部電影的影城做對比******#
                index = theater_name.index(str(place_NAME))           #取得place在其中的index索引
                five_movie_place_time.append(movie_time_list[index])  #將對應的時刻表加入進來
                movie_time_times = movie_time_times + 1

                if 'vicinity' in nearby_place[pnum]:
                    place_LOCATION = nearby_place[pnum]['vicinity']  # 影城的地點位置資訊
                else:
                    place_LOCATION = '缺失位置資訊'
                if 'plus_code' in nearby_place[pnum] and 'compound_code' in nearby_place[pnum]['plus_code']:
                    place_city_INFO = nearby_place[pnum]['plus_code']['compound_code'].split(' ')[-1]  # 影城在哪一個城市
                    if place_city_INFO.lower().find('china') != -1:
                        bool_inCHN = True
                else:
                    place_city_INFO = '缺失城市訊息'
                print(place_ID+","+place_NAME+","+place_LOCATION+","+place_city_INFO)

                # 利用place的API得到影城詳細資訊
                place_detail = gmaps.place(
                    place_id=place_ID,
                    language='zh-TW',
                    fields=['international_phone_number', 'rating', 'website', 'photo']
                )
                if 'international_phone_number' in place_detail['result']:
                    place_PHONE = place_detail['result']['international_phone_number'].replace(" ","") # 影城的電話資訊
                else:
                    place_PHONE = '缺失電話資訊'
                if 'website' in place_detail['result']:
                    place_WEBSITE = place_detail['result']['website']                  # 影城的網址
                    bool_WEBSITE = True
                else:
                    place_WEBSITE = 'https://www.google.com.tw/search?q='+place_NAME
                    bool_WEBSITE = False

                # ******到Firebase存取影城Logo圖片部分*******#
                docum_id = place_NAME
                users_ref = db.collection("電影院資料").document(docum_id)
                doc = users_ref.get()
                if doc.to_dict() == None:
                    docum_id = '找不到圖片'
                    users_ref = db.collection("電影院資料").document(docum_id)
                    doc = users_ref.get()
                    img_url = doc.to_dict()['Logo']
                else:
                    img_url = doc.to_dict()['Logo']
                # print(img_url) #測試BUG

                # ******橫向捲軸部分*******#
                if bool_WEBSITE == True:
                    carouselcolumn=CarouselColumn(
                        thumbnail_image_url=img_url,  # 影城的圖片
                        title=place_NAME,     # 影城的名字
                        text="位置資訊:"+place_LOCATION+"\n"+"聯絡電話："+place_PHONE,  # 影城的位置
                        actions=[
                            PostbackTemplateAction(
                                label='電影時刻表',
                                text='查看目前「'+place_NAME+'」'+'中「'+str(user_movie).strip()+'」的電影時刻表',
                                data='時刻表 '+str(x.hour)+'@@'+str(x.minute)+'@@'+str(user_movie).strip()+'@@'+place_NAME+'@@'+five_movie_place_time[movie_time_times]
                            ),
                            URITemplateAction(
                                label='導航',
                                uri='https://www.google.com/maps/dir/?api=1&destination='+place_NAME.replace(" ","%2C")
                            ),
                            URITemplateAction(
                                label='影城網址',
                                uri=place_WEBSITE
                            )
                        ]
                    )
                else:
                    carouselcolumn = CarouselColumn(
                        thumbnail_image_url=img_url,  # 影城的圖片
                        title=place_NAME,  # 影城的名字
                        text="位置資訊:" + place_LOCATION + "\n" + "聯絡電話：" + place_PHONE,  # 影城的位置
                        actions=[
                            PostbackTemplateAction(
                                label='電影時刻表',
                                text='查看目前「'+place_NAME+'」'+'中「'+str(user_movie).strip()+'」的電影時刻表',
                                data='時刻表 '+str(x.hour).strip()+'@@'+str(x.minute).strip()+'@@'+str(user_movie).strip()+'@@'+place_NAME+'@@'+five_movie_place_time[movie_time_times]
                            ),
                            URITemplateAction(
                                label='導航',
                                uri='https://www.google.com/maps/dir/?api=1&destination='+place_NAME.replace(" ","%2C")
                            ),
                            URITemplateAction(
                                label='缺失影城網址',
                                uri=place_WEBSITE
                            )
                        ]
                    )
                if bool_inCHN == False:
                    column_list.append(carouselcolumn)

    if len(five_movie_place_time) == 0:
        place_lenth = 0

    # 設定橫向捲軸，將搜尋到的附近電影院資訊用橫向捲軸的形式呈現給使用者
    # 橫向捲軸最多可以設定十個
    if place_lenth > 0:
        Carousel_template = CarouselTemplate(
            columns=column_list,
            image_aspect_ratio="square",  # 圖片形狀，一共兩個參數。square指圖片1:1，rectangle指圖片1.5:1
            image_size="contain"  # 圖片size大小設定，一共兩個參數。cover指圖片充滿畫面，contain指縮小圖片塞到畫面
        )
        line_bot_api.push_message(
            event.source.user_id,
            TemplateSendMessage(alt_text="為您找到了附近電影院的資訊", template=Carousel_template) #將餐廳的圖片等資訊傳送給使用者
        )
    else:
        line_bot_api.push_message(
            event.source.user_id, TextSendMessage('對不起，您搜索的地方附近沒有電影院有上映這部電影')
        )

#*****使用者發送文字訊息的時候時候*****#
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id  # 取得使用者的user_id
    Ftext = event.message.text
    token = list(event.message.text)
    if event.message.text == "獲取上映中的電影推薦":
        Ftext = event.message.text
        get_movie_releasenow(user_id)
    elif event.message.text == "獲取即將上映的電影推薦":
        Ftext = event.message.text
        get_movie_comingsoon(user_id)
    elif str(event.message.text).split('\n')[0] == "我想看":
        Ftext = str(event.message.text.replace('\n',''))
        text = "親"+'\n'+"請按左下角的「➕」功能,找到「位置信息」的按鈕並發送您的位置"+'\n'+'我們將為您推薦附近有上映這部電影的影城'
        line_bot_api.push_message(event.source.user_id, TextSendMessage(text=text))
    elif str(event.message.text).split('「')[0] == "查看目前":
        Ftext = str(event.message.text)

    elif token[0] == "#":  # 上映中的電影
        keyword_search_releasing(user_id, Ftext.split("#")[1])

    elif token[0] == "@":  # 即將上映的電影
        keyword_search_coming(user_id, Ftext.split("@")[1])
        print(Ftext.split("@")[1])
    else:
        auto_reply = '親，歡迎來到iMovie' + '\n\n' \
                     + '您可以發送電影的「#關鍵字」，我們將為您確認其是否已經上映' + '\n\n' \
                     + '若是想要查看即將上映的電影，則發送「@關鍵字」' + '\n\n' \
                     + '若是想要查看現在或即將上映的電影有哪些，則選擇下面的「電影先鋒」功能選單'

        line_bot_api.push_message(
            user_id, TextSendMessage('%s' % (auto_reply))
        )

        # *****紀錄使用者動作到Firebase上面做行為分析*****#
    # 取得當下時間
    x = datetime.datetime.now(tz)
    time_now = str(x.year) + '-' + str(x.month) + '-' + str(x.day) + ' ' + '星期' + str(x.date().isoweekday()) + ' ' + str(x.hour) + ':' + str(x.minute) + ':' + str(x.second)
    # 將使用者的ID上傳到Firebase上面方便之後進行推播
    users_ref = db.collection("使用者ID以及動作紀錄").document(user_id)
    doc_User_action = {  # 傳送每一筆電影的「英文名稱」到 隨機推薦電影清單/上映中
        "%s" % (str(time_now)): "%s" % (str(Ftext))
    }
    try:
        users_ref.update(doc_User_action)  # 若Firebase中已經存在該使用者的資訊
    except google.cloud.exceptions.NotFound:
        users_ref.set(doc_User_action)  # 若Firebase中還沒有該使用者的資訊

#*****使用者加入LineBot時候*****#
@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id #取得使用者的user_id
    to = user_id
    link = "https://docs.google.com/forms/d/e/1FAIpQLSeNeVnnTYOc-TVJJQwF6O1GhG6Mu9VbV3lpcESqA2u-NWWjbQ/viewform?usp=pp_url&entry.323500799=" + to #進入Google表單並將使用者的use_id自動填入google表單的身分憑證

    #讓使用者選擇是否填寫電影調查，若使用者選擇是則跳到Google表單部分反之則
    button_template_message = ButtonsTemplate(
        title='尊敬的iMovie新用戶',
        text='打擾您寶貴的幾分鐘時間幫我們填寫一下電影喜好度問卷，我們將根據您的喜好推薦適合您的電影',
        ratio="1.51:1",
        actions=[
            URITemplateAction(
                label='我願意填寫',
                uri='%s' % (link)
            ),
            URITemplateAction(
                label='我不要填寫',
                uri='%s' % (link)
            )
        ]
    )
    line_bot_api.push_message(to, TemplateSendMessage(alt_text="歡迎使用iMovie，電影君在此為您竭誠服務", template=button_template_message))

    #****以下為連接Firebase並紀錄下使用者的動作紀錄****
    x = datetime.datetime.now(tz) # 取得當下時間
    time_now = str(x.year)+' '+str(x.month)+' '+str(x.day)+' '+' '+str(x.date().isoweekday())+' '+str(x.hour)+' '+str(x.minute)+' '+str(x.second)
    text = '加入Line聊天機器人'

    #將使用者的ID上傳到Firebase上面方便之後進行推播
    users_ref = db.collection("使用者ID以及動作紀錄").document(user_id)
    doc_User_action = {  # 傳送每一筆電影的「英文名稱」到 隨機推薦電影清單/上映中
        "%s" % (str(time_now)): "%s" % (str(text))
    }
    try:
        users_ref.update(doc_User_action) # 若Firebase中已經存在該使用者的資訊
    except google.cloud.exceptions.NotFound:
        users_ref.set(doc_User_action) # 若Firebase中還沒有該使用者的資訊


#*****紀錄使用者按下Button的動作包括想看一部電影與預約電影時間*****#
@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id

    x = datetime.datetime.now(tz)  # 取得當下時間
    time_now = str(x.year) + ' ' + str(x.month) + ' ' + str(x.day) + ' ' + ' ' + str(x.date().isoweekday()) + ' ' + str(
        x.hour) + ' ' + str(x.minute) + ' ' + str(x.second)

    if event.postback.data.split('\n')[0] == "我想預約":
        users_ref = db.collection("使用者想預約電影紀錄").document(user_id)
        doc_User_action = {  # 傳送使用者[預約的電影]到 及動作紀錄/user_id
            "%s" % (str(time_now)): "%s " % (event.postback.data.split(' ')[1])
        }
        try:
            users_ref.update(doc_User_action)  # 若Firebase中已經存在該使用者的資訊
        except google.cloud.exceptions.NotFound:
            users_ref.set(doc_User_action)  # 若Firebase中還沒有該使用者的資訊

    elif event.postback.data.split('\n')[0] == "我想看":
        users_ref = db.collection("使用者想看電影紀錄").document(user_id)
        doc_User_action = {  # 傳送使用者[歷史點擊紀錄]到 及動作紀錄/user_id
            "最近一筆資料": "%s " % (event.postback.data.split('\n')[1])
        }
        try:
            users_ref.update(doc_User_action)  # 若Firebase中已經存在該使用者的資訊
        except google.cloud.exceptions.NotFound:
            users_ref.set(doc_User_action)  # 若Firebase中還沒有該使用者的資訊

    elif event.postback.data.split(' ')[0] == "時刻表":
        time_final_text = ''
        theater_text = event.postback.data.split('時刻表')[1].strip().split('@@')[3] #
        mov_text = event.postback.data.split('時刻表')[1].strip().split('@@')[2]
        tim_text = event.postback.data.split('時刻表')[1].strip().split('@@')[4]
        accord_time_hour = event.postback.data.split('時刻表')[1].strip().split('@@')[0]
        accord_time_minu = event.postback.data.split('時刻表')[1].strip().split('@@')[1]

        # print(accord_time_hour) # 測試BUG
        # print(accord_time_minu) # 測試BUG
        # print(tim_text) # 測試BUG

        tim_devide = tim_text.split('\n')
        for tim in tim_devide:
            hour_s = int(tim.strip().split(':')[0])
            minu_s = int(tim.strip().split(':')[1])
            if(hour_s>int(accord_time_hour)):
                time_final_text += tim+'\n'
            elif hour_s==int(accord_time_hour) and (minu_s>=int(accord_time_minu)):
                time_final_text += tim+'\n'
        if time_final_text.strip() != '':
            final_text = '「'+theater_text+'」'+'中'+'「'+mov_text+'」'+'的電影時刻如下:'+'\n'+'*********'+'\n'+time_final_text
            line_bot_api.push_message(user_id, TextSendMessage(text=final_text))
        else:
            final_text = '抱歉，親\n'+'目前「'+theater_text+'」'+'中'+'「'+mov_text+'」沒有您可以觀看的時間'
            line_bot_api.push_message(user_id, TextSendMessage(text=final_text))


# 推播
sched = BackgroundScheduler()
sched.add_job(push_to_user, 'cron', day_of_week='mon-sun', hour='5', minute="20",second="30") #呼叫push_to_user 12~21點之間 每一小時推播一次
sched.start() #執行推播

if __name__ == "__main__":
    app.run()