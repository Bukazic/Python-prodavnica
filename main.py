from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_uploads import UploadSet, IMAGES, configure_uploads
from pymongo import MongoClient
from pprint import pprint

from bson import ObjectId

import hashlib

import time

client = MongoClient('mongodb+srv://mongodb013:mongodb013@mlab013-eubow.mongodb.net/test?retryWrites=true&w=majority')
db = client.mongodb013

users = db.users
items = db.items
sales = db.sales
comments = db.comments

app = Flask(__name__)
app.config['SECRET_KEY'] = 'NEKI RANDOM STRING'
photos = UploadSet('photos', IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = 'static'
configure_uploads(app, photos)


@app.route('/')
@app.route('/index')
def index(): 

    if '_id' not in session: 
        return render_template('index.html', welcome_text = "anonymous")
    user = users.find_one({  
        '_id':ObjectId(session['_id'])
    })
    return render_template('index.html', welcome_text = user['username'])

@app.route('/register', methods = ['GET', 'POST']) 
def register():
    if request.method == 'GET':
        return render_template('register.html') 
    else:
        hash_object = hashlib.sha256(request.form['password'].encode())  
        password_hashed = hash_object.hexdigest()

        if users.find_one({'username': request.form['username']}) is not None: 
            return 'Korisnik vec postoji'

        uname = request.form['username']

        if uname.endswith('@gmail.com') or uname.endswith('@raf.rs'): 
            users.insert_one(
                {
                    'username': request.form['username'],  
                    'password': password_hashed,
                    'type': request.form['type'],
                    'name': request.form['ime'],
                    'last_name': request.form['lastname'],
                    'card_num': request.form['kartica'],
                    'address': request.form['adresa'],
                    'company': request.form['kompanija'],
                    'funds': 10
                }
            )
        else:
            return redirect(url_for('register')) 

        return redirect(url_for('login')) 

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'GET':  
        return render_template('login.html')  
    else:
        hash_object = hashlib.sha256(request.form['password'].encode())  
        password_hashed = hash_object.hexdigest()
        user = users.find_one({
            'username': request.form['username'], 'password': password_hashed
        })
        if user is None:          
            return 'Korisnika nema u bazi, pokusaj ponovo!'
        session['_id'] = str(user['_id'])
        session['type'] = user['type']
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/home')
def home():
    user = users.find_one({
        '_id':ObjectId(session['_id'])
    })

    popular = [item for item in items.find().sort('visits', -1)]
    return render_template('home.html', items = popular, user = user, type = user['type'])

@app.route('/all-sellers')
def all_sellers():
    sellers_list = []
    for user in users.find({
        'type': 'prodavac'
        }):
        user['_id'] = str(user['_id'])
        sellers_list.append(user)
    return render_template('all-sellers.html', sellers = sellers_list)
    
@app.route('/sellers/<id>', methods = ['GET', 'POST'])
def seller(id):
    seller = users.find_one({
        '_id': ObjectId(id)
    })

    if seller is None:
        return 'Ne postoji taj prodavac'

    my_items = [item for item in items.find({'seller_id': ObjectId(session['_id'])})]

    return render_template('seller.html', user = seller, items = my_items)

@app.route('/items/<id>', methods = ['GET', 'POST'])
def item(id):
    me = users.find_one({
        '_id': ObjectId(session['_id'])
    })

    item = items.find_one({
        '_id': ObjectId(id)
    })

    if item is None:
        return 'Ne postoji takav item'
    item['_id'] = str(item['_id'])
    lista_lajkova = []
    if 'liked' in item:
        lista_lajkova = item['liked']

    lista_usernameova = []
    for user in lista_lajkova:
        found_user = users.find_one({
            '_id': ObjectId(user)
        })
        lista_usernameova.append(found_user['username'])

    
    if request.method == 'POST':
        items.delete_one({
            '_id': ObjectId(id)
        })
        return redirect(url_for('all_items'))

    item_comment = [comment for comment in comments.find({
        'item_id': id
    })]

    visits = item['visits'] + 1 

    items.update_one({'_id': ObjectId(id)}, {'$set': {'visits': visits}})

    return render_template('item.html', item = item, lajkovi = len(lista_lajkova), lista_korisnika = lista_usernameova, user = me, all_comments = item_comment)

@app.route('/add-comment/<id>', methods = ['POST'])
def add_comment(id):
    if request.method == 'GET':
        return redirect(url_for('home'))
    else:
        me = users.find_one({
            '_id': ObjectId(session['_id'])
        })

        item_id = ObjectId(id)

        comment_props = {
            'mail': request.form['mail'],
            'content': request.form['content'],
            'time': time.strftime("%d-%m-%Y.%H:%M:%S"),
            'item_id': id
        }

        comments.insert_one(comment_props)

        return redirect(url_for("item", id = item_id))


@app.route('/lajk', methods = ['POST'])
def lajk():
    user_id = session['_id']
    item = items.find_one({
        '_id': ObjectId(request.form['item_id'])
    })
    if item is None:
        return 'Item ne postoji'
    
    lista = []
    if 'liked' in item:
        lista = item['liked']
        if user_id in item['liked']:
            return 'Vec ste lajkovali proizvod!'
    
    lista.append(user_id)
    items.update_one({'_id': ObjectId(request.form['item_id'])}, {'$set': {'liked': lista}})
    return redirect(url_for('item', id = request.form['item_id']))

@app.route('/all-items')
def all_items():
    f_items = [item for item in items.find({'qtt': {'$gt': 0}})]
    return render_template('all-items.html', items = f_items)

@app.route('/myprofile')
def my_profile():
    me = users.find_one({
        '_id': ObjectId(session['_id'])
    })

    if me['type'] == 'admin':
        return redirect(url_for('home'))
    
    if me['type'] == 'kupac':
        return render_template('myprofile.html', user = me)
    
    my_items = [item for item in items.find({
        'seller_id': ObjectId(session['_id'])
    })]

    return render_template('myprofile.html', user = me, items = my_items)

@app.route('/add-funds', methods = ['GET', 'POST'])
def add_funds():
    if request.method == 'GET':
        return redirect(url_for('my_profile'))
    else:
        me = users.find_one({
            '_id': ObjectId(session['_id'])
        })
        money = request.form['funds']
        users.update_one({'_id': ObjectId(session['_id'])}, {'$inc': {'funds': int(money)}})

        return redirect(url_for('my_profile'))

@app.route('/add-item', methods = ['GET', 'POST'])
def add_item():
    if request.method == 'GET':
        return redirect(url_for('my_profile'))
    else:
        if session['type'] != 'prodavac':
            return 'Niste prodavac'

        me = users.find_one({
            '_id': ObjectId(session['_id'])
        })

        item_props = {
            'name': request.form['name'],
            'desc': request.form['desc'],
            'price': int(request.form['price']),
            'qtt': int(request.form['qtt']),
            'visits': 0,
            'likes': 0,
            'seller_id': ObjectId(session['_id']),
            'seller_name': me['username']
        }

        items.insert_one(item_props)

        return redirect(url_for('my_profile'))

# POSEBNA STRANICA ZA BRISANJE KORISNIKA ZA ADMINA
@app.route('/all-users')
def all_users():
    me = users.find_one({
        '_id': ObjectId(session['_id'])
    })

    if me['type'] != 'admin':
        return 'Niste admin'

    found_users = []
    for user in users.find({}):
        user['_id'] = str(user['_id'])
        found_users.append(user)

    return render_template('users.html', users = found_users, me = me)

@app.route('/delete-user', methods = ['POST'])
def delete_user():
    me = users.find_one({
        '_id': ObjectId(session['_id'])
    })

    if me['type'] != 'admin':
        return 'Niste admin'
    
    deleted_users = users.find_one({
        '_id': ObjectId(request.form['user_id'])
    })
    if deleted_users['type'] == 'prodavac':
        item = items.delete_many({
            'seller_id': ObjectId(request.form['user_id'])
        })

    user = users.delete_one({
        '_id': ObjectId(request.form['user_id'])
    })

    return redirect(url_for('all_users'))

@app.route('/buy', methods = ['POST'])
def buy():

    me = users.find_one({
        '_id': ObjectId(session['_id'])
    })

    item = items.find_one({
        '_id': ObjectId(request.form['item_id'])
    })

    sum_price = int(request.form['kolicina']) * int(item['price'])
 
    print(item['price'])

    funds = int(me['funds'])

    print(funds)
    
    if sum_price > funds :
        return 'Nemate dovoljno novca na racunu!'

    new_sale = {
        'seller_id': item['seller_id'],
        'user_id': me['_id'],
        'price': sum_price,
        'item': item['_id']
    }

    new_qtt = int(item['qtt']) - int(request.form['kolicina'])
    sum_funds = int(me['funds']) - sum_price
    users.update_one({
        '_id': ObjectId(session['_id'])}, {"$set": {"funds": sum_funds}}
    )
    items.update_one({'_id': ObjectId(request.form['item_id'])}, {"$set": {'qtt': new_qtt}})

    sales.insert_one(new_sale)

    return redirect(url_for('my_profile'))

if __name__ == '__main__':
    app.run(debug=True)