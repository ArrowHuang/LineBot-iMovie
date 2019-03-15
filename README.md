# LineBot-iMovie
iMovie is a LineBot for people who like watching movies. It combines chatbot with opinion mining and context-awareness technologies.

1) **「moviebot.py」** is main code for LineBot.    
2) **「Yahoo_Movie_Comingsoon_2_Firebase.py」** is a web crawler code. It use spider to collect all movies that will come soon around Taiwan.  
3) **「Yahoo_Movie_Releasing_2_Firebase.py」** is also a web crawler code. It use spider to collect all movies that are releasing now around Taiwan.    
4) **「Yahoo_Movie_Score_2_Firebase.py」** is a web crawler code. It use spider to collect movie informations including movie score, film review and so on from **IMDB**, **Yahoo Movie** and **Rotten Tomatoes**. 
What's more, It also uses Google NLP API to analysis and calculate the movie score according to a simple rule I made.  
5) **「How to put LineBot into Heroku in Mac OS.txt」** is a guide to teach users how to push their codes to Heroku.  

Pease note the following issues if you want to build your own LineBot:  
1) You should go to __Line Developer__ to apply for a api key.  
   And put the api key into **moviebot.py**  
2) You should go to __Google Firebase__, __Google Map__ to and __Google NLP API__ apple for api keys.  
   And put api keys into **moviebot.py**, **Yahoo_Movie_Comingsoon_2_Firebase.py**, **Yahoo_Movie_Releasing_2_Firebase.py** and **Yahoo_Movie_Score_2_Firebase.py**
 
More details pls visit [Line Developer](https://developers.line.biz/en/), [Google Firebase](https://firebase.google.com/?gclid=CjwKCAjw96fkBRA2EiwAKZjFTQpwybV28r42vkkUeoGbNMC5aROxaIrsCT_9EFAoj-KH5Zm9q8U2FRoCrBEQAvD_BwE) and [Heroku](https://www.heroku.com/). 
  
  
![image](https://github.com/ArrowHuang/LineBot-iMovie/blob/master/Screenshots/reference.png)    
 
![image](https://github.com/ArrowHuang/LineBot-iMovie/blob/master/Screenshots/structure1.png)    

![image](https://github.com/ArrowHuang/LineBot-iMovie/blob/master/Screenshots/structure2.png)     
 
