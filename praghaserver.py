from flask import Flask, request, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Integer, ForeignKey
import xml.etree.ElementTree as Etree
import hashlib

from playback import stream_audio

import config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# SQLAlchemy Models.
class Title(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    def __init__(self, name):
        self.name = name

class Artist(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True, unique=True)

    def __init__(self, name):
        self.name = name

class Album(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True, unique=True)

    def __init__(self, name):
        self.name = name

class Genre(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True, unique=True)

    def __init__(self, name):
        self.name = name

class Comment(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True, unique=True)

    def __init__(self, name):
        self.name = name

class Track(db.Model):
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False, unique=True)
    title_id = Column(ForeignKey('title.id'), nullable=True, default=None)
    artist_id = Column(ForeignKey('artist.id'), nullable=True, default=None)
    album_id = Column(ForeignKey('album.id'), nullable=True, default=None)
    genre_id  = Column(ForeignKey('genre.id'), nullable=True, default=None)
    comment_id = Column(ForeignKey('comment.id'), nullable=True, default=None)
    track = Column(Integer, default=None, nullable=True)
    year = Column(Integer, nullable=False)
    length = Column(Integer, nullable=False)

    title = db.relationship('Title', backref=db.backref('Titles', lazy='dynamic'))
    artist = db.relationship('Artist', backref=db.backref('Artists', lazy='dynamic'))
    album = db.relationship('Album', backref=db.backref('Albums', lazy='dynamic'))
    genre = db.relationship('Genre', backref=db.backref('Genres', lazy='dynamic'))
    comment = db.relationship('Comment', backref=db.backref('Comments', lazy='dynamic'))

    def __init__(self, filename, title_id, artist_id, album_id, genre_id, comment_id, track, year, length):
        self.filename = filename
        self.title_id = title_id
        self.artist_id = artist_id
        self.album_id = album_id
        self.genre_id = genre_id
        self.comment_id = comment_id
        self.track = track
        self.year = year
        self.length = length

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __repr__(self):
        return '<User %r>' % self.username

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(80), nullable=False, unique=True)
    user = db.Column(db.Integer, nullable=False)
    expire = db.Column(db.Integer, nullable=False)

    def __init__(self, token, user, expire):
        self.token = token
        self.user = user
        self.expire = expire

    def __repr__(self):
        return '<Token %r>' % self.token

# Standard routes.
@app.route("/")
def hello_world():
    return "Pragha Server!."


@app.route('/about')
def about():
    return 'A Music Server for Pragha until now compatible with Ampache..'


# Helper to ivalid login.
def invalid_login():
    n_root = Etree.Element('root')
    Etree.SubElement(n_root, 'error', code='401').text = 'Error Invalid Handshake - Invalid Username/Password'
    txt =  Etree.tostring(n_root, encoding='utf8', method='xml')
    response = Response(txt)
    response.status_code = 401
    response.headers["Content-Type"] = "application/xml"
    return response


# Helper to session expired.
def session_expired():
    n_root = Etree.Element('root')
    Etree.SubElement(n_root, 'error', code='401').text = 'Session Expired'
    txt =  Etree.tostring(n_root, encoding='utf8', method='xml')
    response = Response(txt)
    response.status_code = 401
    response.headers["Content-Type"] = "application/xml"
    return response


# Helper to invalid request.
def invalid_request():
    n_root = Etree.Element('root')
    Etree.SubElement(n_root, 'error', code='405').text = 'Invalid Request'
    txt =  Etree.tostring(n_root, encoding='utf8', method='xml')
    response = Response(txt)
    response.status_code = 405
    response.headers["Content-Type"] = "application/xml"
    return response

# Helper to invalid request.
def resource_not_found():
    n_root = Etree.Element('root')
    Etree.SubElement(n_root, 'error', code='404').text = 'Resorce Fot Found'
    txt =  Etree.tostring(n_root, encoding='utf8', method='xml')
    response = Response(txt)
    response.status_code = 404
    response.headers["Content-Type"] = "application/xml"
    return response


#/server/xml.server.php?action=ping&auth=AUTH
def do_ping():
    auth = request.args.get('auth')
    dbSession = Session.query.filter_by(token=auth).first()

    app.logger.error('Ping: ' + str(dbSession))

    if dbSession is None:
        return session_expired()

    # Extend session
    dbSession.expire+=60*60
    db.session.commit()

    # Response.
    n_root = Etree.Element('root')
    Etree.SubElement(n_root, "version").text = '350001'
    txt =  Etree.tostring(n_root, encoding='utf8', method='xml')

    response = Response(txt)
    response.status_code = 200
    response.headers["Content-Type"] = "application/xml"
    return response


#/server/xml.server.php?action=handshake&auth=PASSPHRASE&timestamp=TIMESTAMP_SALT&version=350001&user=USERNAME
@app.route("/handshake", methods=['GET'])
def do_handshake():
    auth = request.args.get('auth')
    timestamp = request.args.get('timestamp')
    username = request.args.get('user')

    # Check user..
    dbUser = User.query.filter_by(username=username).first()
    if dbUser is None:
        return invalid_login()

    pass_hash = hashlib.sha256(str(dbUser.password).encode('utf8')).hexdigest()
    auth_cmp = hashlib.sha256(str(timestamp).encode('utf8')+str(pass_hash).encode('utf8')).hexdigest()

    if auth != auth_cmp:
        return invalid_login()

    # Add session
    expire = int(timestamp)+60*60
    dbSession = Session(auth, dbUser.id, expire)
    db.session.add(dbSession)
    db.session.commit()

    # Check..
    dbSession2 = Session.query.filter_by(token=auth).first()
    app.logger.error('Handshake: ' + auth + ' => ' + str(dbSession2))

    # Response
    n_root = Etree.Element('root')
    Etree.SubElement(n_root, "version").text = '350001'
    Etree.SubElement(n_root, 'auth').text = auth_cmp #TODO: Generate another random key.
    Etree.SubElement(n_root, "songs").text = str(Track.query.count())
    txt =  Etree.tostring(n_root, encoding='utf8', method='xml')

    response = Response(txt)
    response.status_code = 200
    response.headers["Content-Type"] = "application/xml"
    return response


# /server/xml.server.php?action=songs&offset=500&limit=500&auth=15d011d477c847330f29bcb23502cd7b92f03745b5712932467fb9dba4d73a4f
@app.route("/songs", methods=['GET'])
def do_songs():
    auth = request.args.get('auth')
    offset = request.args.get('offset')
    limit = request.args.get('limit')

    db.session.commit()
    dbSession = Session.query.filter_by(token=auth).first()

    app.logger.error('Songs to auth: ' + auth + " => " + str(dbSession))

    #TODO: Check lifetime...
    if dbSession is None:
        return session_expired()

    dbsongs = Track.query.offset(offset).limit(limit).all()

    n_root = Etree.Element('root')
    for song in dbsongs:
        song_root = Etree.Element('song')
        song_root.set('id', str(song.id))
        if song.track > 0:
            Etree.SubElement(song_root, 'track').text = str(song.track)
        if song.title != None:
            Etree.SubElement(song_root, 'title').text = str(song.title.name)
        if song.artist != None:
            Etree.SubElement(song_root, 'artist').text = str(song.artist.name)
        if song.album != None:
            Etree.SubElement(song_root, 'album').text = str(song.album.name)
        if song.genre != None:
            Etree.SubElement(song_root, 'genre').text = str(song.genre.name)
        if song.comment != None:
            Etree.SubElement(song_root, 'comment').text = str(song.comment.name)
        if song.track > 0:
            Etree.SubElement(song_root, 'track').text = str(song.track)
        if song.year > 0:
            Etree.SubElement(song_root, 'year').text = str(song.year)
        if song.length > 0:
            Etree.SubElement(song_root, 'time').text = str(song.length)
        Etree.SubElement(song_root, 'url').text = config.PUBLIC_DOMAIN + "/play/index.php?type=song&oid="+str(song.id)+"&ssid="+str(auth)+"&uid=5&player=api&name="+str(song.id)
        n_root.append(song_root)

    txt = Etree.tostring(n_root)
    response = Response(txt)
    response.status_code = 200
    response.headers["Content-Type"] = "application/xml"
    return response


# play/index.php?type=song&SONG_ID=70&uid=USER_ID&player=api&name=SONG_NAME&ssid=AUTH
@app.route('/play/index.php', methods=['GET'])
def dp_play():
    auth = request.args.get('ssid')
    dbSession = Session.query.filter_by(token=auth).first()

    #TODO: Check lifetime...
    if dbSession is None:
        return session_expired()

    stream = stream_audio()
    if stream == None:
        return resource_not_found()
    else:
        return stream


# /server/xml.server.php?action=ACTION
@app.route('/server/xml.server.php', methods=['GET'])
def server():
    action = request.args.get('action')
    if action == 'handshake':
        return do_handshake()
    elif action == 'ping':
        return do_ping()
    elif action == 'songs':
        return do_songs()
    else:
        return invalid_request()


def create_app():
    db.init_app(app)
    with app.app_context():
        db.create_all()
        db.session.commit()
    return app

if __name__ == '__main__':
    create_app().run()
