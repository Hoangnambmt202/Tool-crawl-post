import json
import mysql.connector
from bs4 import BeautifulSoup
import requests
import Objectlink as obl
import CameraObject as camob
import openai
from googletrans import Translator

def get_price(tag_price):
    price = ''
    price = tag_price.text.strip()
    price = price.replace(',', '')
    price = price.replace('.', '')
    price = price.replace('đ', '')
    price = price.replace('₫', '')
    
    price = price.replace('Liên hệ', '')
    if price == '':
        price = '0'
    return price

def dich( nd ):
    translator = Translator()
    translated_text = translator.translate(nd, src='en', dest='vi').text
    print(translated_text)
    # Create a chat completion
    print ('*************ai dịch: ')
    # if(len(translated_text)> 150):
    #     response = openai.ChatCompletion.create(
    #         model="gpt-4",
    #         messages=[
    #             {"role": "user", "content": "viết lại:" + translated_text}
    #         ]
    #     )
    #     # Print the response
    #     kq = response.choices[0].message["content"]
    #     print(kq)
    #     if(kq and kq != ''):
    #         translated_text = kq
    
    return translated_text
def check_cam_url1(url_id,cam_url,name):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="baivietphothong"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query

    select_query = "SELECT * FROM bot_news where title like %s and url like %s"
    data = ("%" + name + "%","%" + cam_url + "%")
    # Execute the SELECT query
    cursor.execute(select_query,data)

    # Fetch all rows
    rows = cursor.fetchall()

    # Iterate over the rows and print each row
    if len(rows) > 0:
        kq = 0
    else:
        kq = 1
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()
    return kq

def check_cam_url(url_id,cam_url,name):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="baivietphothong"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query

    select_query = "SELECT * FROM bot_news where title like %s and url_id = %s"
    data = ("%" + name + "%","" + url_id + "")
    # Execute the SELECT query
    cursor.execute(select_query,data)

    # Fetch all rows
    rows = cursor.fetchall()

    # Iterate over the rows and print each row
    if len(rows) > 0:
        kq = 0
    else:
        kq = 1
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()
    return kq

def check_cam_url_pro(url_id,cam_url,name):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="baivietphothong"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query

    select_query = "SELECT * FROM bot_product where title like '" + name+"' and (url_id = "+url_id+" and url =  '"+cam_url+"')"
    select_query = "SELECT * FROM bot_product where title like '" + name+"' or (url_id = "+url_id+" and url =  '"+cam_url+"')"
   
    # Execute the SELECT query
    cursor.execute(select_query)

    # Fetch all rows
    rows = cursor.fetchall()

    # Iterate over the rows and print each row
    if len(rows) > 0:
        kq = 0
    else:
        kq = 1
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()
    return kq
   

def read_products( ):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="baivietphothong"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query

    select_query = "SELECT * FROM bot_product where upload = 0 order by id desc"
    data = ()
    # Execute the SELECT query
    cursor.execute(select_query,data)

    # Fetch all rows
    rows = cursor.fetchall()

    # Iterate over the rows and print each row
   
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()
    if len(rows) > 0:
        return rows
    else:
        return None
     
def read_news( ):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="baivietphothong"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query

    select_query = "SELECT * FROM bot_news where upload = 0 order by id asc"
    data = ()
    # Execute the SELECT query
    cursor.execute(select_query,data)

    # Fetch all rows
    rows = cursor.fetchall()

    # Iterate over the rows and print each row
   
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()
    if len(rows) > 0:
        return rows
    else:
        return None
     
def update_upload_hv(id ):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="vuihoc"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query
    insert_query = "update hv_book set doc = 1 where id = %s" 
    # Data to be inserted
    print('save_data')
    data = ( id, )  # Replace with your actual data
    # Execute the INSERT query
    cursor.execute(insert_query, data)
    # Commit changes to the database
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()   
def read_hocvui( ):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="vuihoc"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query

    select_query = "SELECT * FROM hv_book where doc = 0 order by id desc"
    data = ()
    # Execute the SELECT query
    cursor.execute(select_query,data)

    # Fetch all rows
    rows = cursor.fetchall()

    # Iterate over the rows and print each row
   
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()
    if len(rows) > 0:
        return rows
    else:
        return None
     
def fetch_webpage(url):
    requests.packages.urllib3.disable_warnings( )
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36'
    }
    response = requests.get(url, headers=headers,verify=False)
    # response = requests.get(url)
    if response.status_code == 200:
        return BeautifulSoup(response.text, 'html.parser')
    else:
        print("Failed to fetch the webpage:", response.status_code)
        return None

def find_substring(main_string, substring):
    try:
        index = main_string.index(substring)
    except ValueError:
        index = -1
    return index

def save_data_cam(url_id,cam):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="baivietphothong"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query
 
    photo = ""
    for op in cam.photos:
        if(photo != ""):
            photo += ","
        if op!= None:
            photo += op
    insert_query = "INSERT INTO bot_news (url_id,title,url,photo,content,summary,cat_id,date_publish) "
    insert_query += " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    # Data to be inserted
    
    data = (url_id,cam.name,cam.url, photo,cam.description,cam.short,cam.cat_id,cam.date_publish)  # Replace with your actual data
    # Execute the INSERT query
    cursor.execute(insert_query, data)
    # Commit changes to the database
    print('luu data')
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()

def save_data(url_id,cam,cat_id):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="baivietphothong"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query

    select_query = "SELECT * FROM bot_news where url_id = "+url_id+" and title like %s"
     
    data = ("%" + cam.name + "%",)
    # Execute the SELECT query
    cursor.execute(select_query,data)

    # Fetch all rows
    rows = cursor.fetchall()

    # Iterate over the rows and print each row
    if len(rows) > 0:
        print ('bài viết đã có!')
        return
    photo = ""
    for op in cam.photos:
        if(photo != ""):
            photo += ","
        if op!= None:
            photo += op
    
     
    insert_query = "INSERT INTO bot_news (url_id,title,url,photo,content,summary,cat_id,tags) "
    insert_query += " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    # Data to be inserted
    # print('save_data: ' + cam.description)
    data = (url_id,cam.name,cam.url, photo,cam.description,cam.summary,cat_id,cam.tags)  # Replace with your actual data
    # Execute the INSERT query
    cursor.execute(insert_query, data)
    print ('đã thêm thành công!')
    # Commit changes to the database
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()

def save_product( title,slug,price,photo,  summary,description,cat_id ):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="tanphat"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query

    select_query = "SELECT * FROM products where title like %s"
     
    data = ("%" + title + "%",)
    # Execute the SELECT query
    cursor.execute(select_query,data)

    # Fetch all rows
    rows = cursor.fetchall()
    # Iterate over the rows and print each row
    if len(rows) > 0:
        conn.commit()
        cursor.close()
        conn.close()
        return
    insert_query = "INSERT INTO products (title,slug,price,photo,summary,description,cat_id) "
    insert_query += " VALUES (%s,%s,%s,%s,%s,%s,%s)"
    data = ( title ,slug,price,photo,summary,description,cat_id )  # Replace with your actual data
    cursor.execute(insert_query, data)
    conn.commit()
    cursor.close()
    conn.close()    
def save_category( title,slug ):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="tanphat"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query

    select_query = "SELECT * FROM categories where title like %s"
     
    data = ("%" + title + "%",)
    # Execute the SELECT query
    cursor.execute(select_query,data)

    # Fetch all rows
    rows = cursor.fetchall()
    # Iterate over the rows and print each row
    if len(rows) > 0:
        conn.commit()
        cursor.close()
        conn.close()
        return
    insert_query = "INSERT INTO categories (title,slug) "
    insert_query += " VALUES (%s,%s)"
    data = ( title ,slug )  # Replace with your actual data
    cursor.execute(insert_query, data)
    conn.commit()
    cursor.close()
    conn.close()
def get_category_id( title ):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="tanphat"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query

    select_query = "SELECT * FROM categories where title like %s"
     
    data = ("%" + title + "%",)
    # Execute the SELECT query
    cursor.execute(select_query,data)

    # Fetch all rows
    rows = cursor.fetchall()
    # Iterate over the rows and print each row
    kq = 0
    if len(rows) > 0:
        kq = rows[0][0]
    conn.commit()
    cursor.close()
    conn.close()
    return kq
def update_pro_upload_new(id ):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="baivietphothong"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query
    insert_query = "update bot_product set upload = 1 where id = %s" 
    # Data to be inserted
    print('save_data')
    data = ( id, )  # Replace with your actual data
    # Execute the INSERT query
    cursor.execute(insert_query, data)
    # Commit changes to the database
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()
def update_upload_new(id ):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="baivietphothong"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query
    insert_query = "update bot_news set upload = 1 where id = %s" 
    # Data to be inserted
    print('save_data')
    data = ( id, )  # Replace with your actual data
    # Execute the INSERT query
    cursor.execute(insert_query, data)
    # Commit changes to the database
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()

def update_upload_fail(id ):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="baivietphothong"
    )
    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()
    # Define the INSERT query
    insert_query = "update bot_news set upload = 3 where id = %s" 
    # Data to be inserted
    print('save_data')
    data = ( id, )  # Replace with your actual data
    # Execute the INSERT query
    cursor.execute(insert_query, data)
    # Commit changes to the database
    conn.commit()
    # Close cursor and connection
    cursor.close()
    conn.close()



