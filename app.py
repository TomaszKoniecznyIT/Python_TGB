import os
from dotenv import load_dotenv
from flask import Flask, request, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

db = SQLAlchemy(app)


def token_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')    
        if not token:
            return {"message": "Token is missing!"}
        try:
            payload = jwt.decode(token.split(' ')[1], app.config["SECRET_KEY"],algorithms='HS256')           
        except:
            return {"message": "Invalid Token!"}
        return func(*args, **kwargs)
    return decorated


# user model with password hashing
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120),unique=True, nullable=False)
    password_hash = db.Column(db.String(360), nullable=False)
    is_manager = db.Column(db.Boolean, nullable=False, default=True)

    @property
    def password(self):
        raise ArithmeticError("Password is not a readable attribute!")
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self) -> str:
        return f'User email: {self.email} password: {self.password_hash}'
    

class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    shop_code = db.Column(db.String(15), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self) -> str:
        return f'Shop: {self.name}'


class Target(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.DateTime, nullable=False)
    target = db.Column(db.Float,nullable=False)
    id_shop = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)

    def __repr__(self) -> str:
        return f'Target: {self.target} Month: {self.month}'


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.DateTime, nullable=False)
    total = db.Column(db.Float, nullable=False)
    id_shop = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)

    def __repr__(self) -> str:
        return f'Day: {self.day} total: {self.total}'


@app.route('/users/signup', methods=['POST'])
def add_user():
    email = request.json['email']
    password = request.json['password']
    confirm_password = request.json['confirm_password']

    if (password != confirm_password):
        return {"message": 'The passwords provided are different'}, 400
    
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return {"message": f'User {user.email} added.'}, 201
    else: 
        return {"message": 'User already exists'}, 409


@app.route('/users/login', methods=['POST'])
def login_user():
    email = request.json['email']
    password = request.json['password']

    user = User.query.filter_by(email=email).first()
    passed = user.verify_password(password)
    
    if user is not None and passed:
        token = jwt.encode({
            'user': email,
            'is_manager': user.is_manager,
            'expiration' : str(datetime.utcnow() + timedelta(seconds=1800))
        },
            app.config['SECRET_KEY'], algorithm='HS256')
        return {'message':"The token is generated", 'token': token}, 200
    else:
        return {'message':"Unable to verify"}, 403 


@app.route('/new_shop', methods=['POST'])
@token_required
def add_shop():
    name = request.json['name']
    shop_code = request.json['shop_code']
    email = request.json['email']
    password = request.json['password']
    confirm_password = request.json['confirm_password']

    if (password != confirm_password):
        return {"message": 'The passwords provided are different'}, 400
    
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(email=email, password=password, is_manager=False )
        db.session.add(user)
        db.session.commit()

        shop = Shop(name=name, shop_code=shop_code, user_id=user.id)
        db.session.add(shop)
        db.session.commit()

        return {"message": f'Shop {user.email} added.'}, 201
    else: 
        return {"message": 'Shop already exists'}, 409
    

@app.route('/shops_list')
def get_shops_list():
    shops_data=Shop.query.all()
    shops=[{'id': shop.id, 'name': shop.name, 'shop_code': shop.shop_code, 'user_id':shop.user_id} for shop in shops_data]  
    return {'shops': shops}, 200


@app.route('/shops_targets')
def get_shops_targets():
    shops_targets_data = db.session.query(Shop, Target).join(Target)
    targets = [{
        'id': shop.id,
        'name': shop.name,
        'shop_code': shop.shop_code,
        'user_id':shop.user_id,
        'target_id': target.id,
        'month':target.month,
        'target':target.target
    } for shop, target in shops_targets_data]
    return {'targets': targets}, 200



# creating tables in the database
# with app.app_context():
    # from app import db
    # db.create_all()