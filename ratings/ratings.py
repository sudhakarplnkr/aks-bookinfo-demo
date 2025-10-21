#!/usr/bin/env python3
"""
Python port of the original Node.js ratings service.
Supports:
 - GET /ratings/<id>
 - POST /ratings/<id>
 - GET /health

Environment variables supported from original implementation:
 - SERVICE_VERSION (v1, v2, v-faulty, v-delayed, v-unavailable, v-unhealthy)
 - DB_TYPE (mysql or mongodb) when SERVICE_VERSION==v2
 - MYSQL_DB_HOST, MYSQL_DB_PORT, MYSQL_DB_USER, MYSQL_DB_PASSWORD
 - MONGO_DB_URL
"""
import os
import json
import random
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)

SERVICE_VERSION = os.environ.get('SERVICE_VERSION', 'v1')
DB_TYPE = os.environ.get('DB_TYPE', '')

# in-memory store for non-db mode
user_added_ratings = {}

unavailable = False
healthy = True

if SERVICE_VERSION == 'v-unavailable':
    # toggle unavailable every 60 seconds
    import threading
    def toggle_unavailable():
        global unavailable
        unavailable = not unavailable
        threading.Timer(60.0, toggle_unavailable).start()
    toggle_unavailable()

if SERVICE_VERSION == 'v-unhealthy':
    import threading
    def toggle_unhealthy():
        global healthy, unavailable
        healthy = not healthy
        unavailable = not unavailable
        threading.Timer(900.0, toggle_unhealthy).start()
    toggle_unhealthy()


@app.route('/health')
def health():
    if healthy:
        return jsonify({'status': 'Ratings is healthy'})
    else:
        return make_response(jsonify({'status': 'Ratings is not healthy'}), 500)


@app.route('/ratings/<int:product_id>', methods=['GET'])
def get_ratings(product_id):
    # DB-backed v2
    if SERVICE_VERSION == 'v2':
        if DB_TYPE == 'mysql':
            import mysql.connector
            try:
                conn = mysql.connector.connect(
                    host=os.environ.get('MYSQL_DB_HOST'),
                    port=int(os.environ.get('MYSQL_DB_PORT', '3306')),
                    user=os.environ.get('MYSQL_DB_USER'),
                    password=os.environ.get('MYSQL_DB_PASSWORD'),
                    database='test'
                )
                cursor = conn.cursor()
                cursor.execute('SELECT Rating FROM ratings')
                rows = cursor.fetchall()
                first_rating = rows[0][0] if len(rows) > 0 else 0
                second_rating = rows[1][0] if len(rows) > 1 else 0
                return jsonify({'id': product_id, 'ratings': {'Reviewer1': first_rating, 'Reviewer2': second_rating}})
            except Exception as e:
                return make_response(jsonify({'error': 'could not connect to ratings database'}), 500)
            finally:
                try:
                    cursor.close()
                    conn.close()
                except Exception:
                    pass
        else:
            # mongodb
            from pymongo import MongoClient
            try:
                client = MongoClient(os.environ.get('MONGO_DB_URL'))
                db = client['test']
                data = list(db.ratings.find({}))
                first_rating = data[0]['rating'] if len(data) > 0 else 0
                second_rating = data[1]['rating'] if len(data) > 1 else 0
                return jsonify({'id': product_id, 'ratings': {'Reviewer1': first_rating, 'Reviewer2': second_rating}})
            except Exception as e:
                return make_response(jsonify({'error': 'could not connect to ratings database'}), 500)
            finally:
                try:
                    client.close()
                except Exception:
                    pass

    # Non-db modes
    if SERVICE_VERSION == 'v-faulty':
        if random.random() <= 0.5:
            return make_response(jsonify({'error': 'Service unavailable'}), 503)
        else:
            return jsonify(get_local_reviews(product_id))
    elif SERVICE_VERSION == 'v-delayed':
        if random.random() <= 0.5:
            import time
            time.sleep(7)
            return jsonify(get_local_reviews(product_id))
        else:
            return jsonify(get_local_reviews(product_id))
    elif SERVICE_VERSION in ('v-unavailable', 'v-unhealthy'):
        if unavailable:
            return make_response(jsonify({'error': 'Service unavailable'}), 503)
        else:
            return jsonify(get_local_reviews(product_id))
    else:
        return jsonify(get_local_reviews(product_id))


@app.route('/ratings/<int:product_id>', methods=['POST'])
def post_ratings(product_id):
    try:
        ratings = request.get_json(force=True)
    except Exception:
        return make_response(jsonify({'error': 'please provide valid ratings JSON'}), 400)

    if SERVICE_VERSION == 'v2':
        return make_response(jsonify({'error': 'Post not implemented for database backed ratings'}), 501)
    else:
        user_added_ratings[product_id] = {'id': product_id, 'ratings': ratings}
        return jsonify(get_local_reviews(product_id))


def get_local_reviews(product_id):
    if product_id in user_added_ratings:
        return user_added_ratings[product_id]
    return {'id': product_id, 'ratings': {'Reviewer1': 5, 'Reviewer2': 4}}


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('usage: %s port' % (sys.argv[0]))
        sys.exit(-1)
    port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port)
