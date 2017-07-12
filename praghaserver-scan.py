#!/usr/bin/env python3
from flask import Flask
from praghaserver import db, User, Session, Track, Title, Artist, Album, Genre, Comment

from mediafile import MediaFile
import argparse
import os, sys

from progress.spinner import Spinner
from progress.bar import Bar

import config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

spinner = Spinner('Searching music to scan... ')

def get_title(title):
    id = 0
    dbTitle = Title.query.filter_by(name=title).first()
    if dbTitle != None:
        id = dbTitle.id
    return id

def new_title (title):
    dbTitle = Title(title)
    db.session.add(dbTitle)
    #db.session.commit()
    return get_title(title)

def get_artist(artist):
    id = 0
    dbArtist = Artist.query.filter_by(name=artist).first()
    if dbArtist != None:
        id = dbArtist.id
    return id

def new_artist (artist):
    dbArtist = Artist(artist)
    db.session.add(dbArtist)
    #db.session.commit()
    return get_artist(artist)

def get_album(album):
    id = 0
    dbAlbum = Album.query.filter_by(name=album).first()
    if dbAlbum != None:
        id = dbAlbum.id
    return id

def new_album (album):
    dbAlbum = Album(album)
    db.session.add(dbAlbum)
    #db.session.commit()
    return get_album(album)

def get_genre(genre):
    id = 0
    dbGenre = Genre.query.filter_by(name=genre).first()
    if dbGenre != None:
        id = dbGenre.id
    return id

def new_genre (genre):
    dbGenre = Genre(genre)
    db.session.add(dbGenre)
    #db.session.commit()
    return get_genre(genre)

def get_comment(comment):
    id = 0
    dbComment = Comment.query.filter_by(name=comment).first()
    if dbComment != None:
        id = dbComment.id
    return id

def new_comment (comment):
    dbComment = Comment(comment)
    db.session.add(dbComment)
    #db.session.commit()
    return get_comment(comment)

def add_item_db (filename):
    item = MediaFile(filename)
    if item == None:
        return

    # Title and artist are mandatory,
    if item.artist != None and item.title != None:
        # Ignore dup tracks..
        if Track.query.filter_by(filename=filename).first() != None:
            return

        # Handle nulls.
        track = 0
        if item.track != None:
            track = item.track

        year = 0
        if item.year != None:
            year = item.year

        album = ""
        if item.album != None:
            album = item.album

        genre = ""
        if item.genre != None:
            genre = item.genre

        comment = ""
        if item.comments != None:
            comment = item.comments

        # Get id or append new tag,
        titleId = get_title(item.title)
        if titleId == 0:
            titleId = new_title(item.title)

        artistId = get_artist(item.artist)
        if artistId == 0:
            artistId = new_artist(item.artist)

        albumId = get_album(album)
        if albumId == 0:
            albumId = new_album(album)

        genreId = get_genre(genre)
        if genreId == 0:
            genreId = new_genre(genre)

        commentId = get_comment(comment)
        if commentId == 0:
            commentId = new_comment(comment)

        dbTrack = Track(filename, titleId, artistId, albumId, genreId, commentId, track, year, item.length)
        db.session.add(dbTrack)
        #db.session.commit()
    else:
        with open("error.txt", "a") as myfile:
            myfile.write("Missing tag for: " + filename + "\n")

def scan_folder (bar, path):
    for item in os.listdir(path):
        fullpath = os.path.join(path, item)
        if os.path.isdir (fullpath):
            scan_folder (bar, fullpath)
        else:
            add_item_db (fullpath)
            bar.next()

def count_folder (path):
    fileCount = 0
    for item in os.listdir(path):
        fullpath = os.path.join(path, item)
        if os.path.isdir (fullpath):
            spinner.next()
            fileCount += count_folder (fullpath)
        else:
            fileCount += 1
    return fileCount

def update_db(a):
    # Create table.
    db.create_all()

    # Count files to scan
    filesToScan = count_folder (config.MUSIC_DIR)

    # Import new songs
    bar = Bar('Importing your music collection', max=filesToScan)
    scan_folder (bar, config.MUSIC_DIR)
    bar.finish()

    # Commits new songs.
    db.session.commit()


def clean_db(a):
    db.session.query(Track).delete()
    db.session.commit()
    db.session.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage Music Database for PraghaServer')
    parser.add_argument('operation', nargs='+', choices=['update', 'clean'], help='Operation')
    args = parser.parse_args()
    db.app = app
    db.init_app(app)
    with app.app_context():
        op = {
            'update': update_db,
            'clean': clean_db
        }[args.operation[0]]
    exit(op(args))
