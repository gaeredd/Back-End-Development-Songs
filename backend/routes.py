from . import app
import os
import json
from flask import jsonify, request
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from bson import json_util
import sys
from bson.json_util import dumps


# Load environment variables
mongodb_service = os.getenv('MONGODB_SERVICE')
mongodb_username = os.getenv('MONGODB_USERNAME')
mongodb_password = os.getenv('MONGODB_PASSWORD')
mongodb_port = os.getenv('MONGODB_PORT', '27017')

# Validate MongoDB service
if not mongodb_service:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

# Construct MongoDB connection URL
try:
    if mongodb_username and mongodb_password:
        url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}:{mongodb_port}"
    else:
        url = f"mongodb://{mongodb_service}:{mongodb_port}"
    client = MongoClient(url)
    db = client.songs
except Exception as e:
    app.logger.error(f"Error connecting to MongoDB: {e}")
    sys.exit(1)

# Helper to load JSON data
def load_data():
    site_root = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(site_root, "data", "songs.json")
    try:
        with open(json_url, "r") as file:
            return json.load(file)
    except Exception as e:
        app.logger.error(f"Error loading JSON file: {e}")
        return []

# Initialize database
songs_list = load_data()
if songs_list:
    db.songs.drop()
    db.songs.insert_many(songs_list)

# Parse MongoDB JSON
def parse_json(data):
    return json.loads(json_util.dumps(data))

# Endpoints
@app.route("/health", methods=["GET"])
def health():
    try:
        client.admin.command('ping')
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route("/count", methods=["GET"])
def count():
    try:
        count = db.songs.count_documents({})
        return jsonify({"count": count}), 200
    except Exception as e:
        app.logger.error(f"Error in /count endpoint: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

@app.route("/song", methods=["GET"])
def songs():
    """Return all songs from the database"""
    try:
        songs_data = db.songs.find({})  # Fetch all documents from the songs collection
        songs_list = json.loads(dumps(songs_data))  # Convert MongoDB cursor to JSON
        return jsonify({"songs": songs_list}), 200  # Return data as JSON with 200 OK status
    except Exception as e:
        print(f"Error in /song endpoint: {e}")
        return jsonify({"error": str(e)}), 500  # Return error if something goes wrong

@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """Return a song by its ID"""
    try:
        song = db.songs.find_one({"id": id})  # Search for a song with the given id
        if song is None:
            return jsonify({"message": "song with id not found"}), 404  # Return error if song not found
        song_data = json.loads(dumps(song))  # Convert MongoDB object to JSON
        return jsonify(song_data), 200  # Return the song as JSON with 200 OK status
    except Exception as e:
        print(f"Error in /song/<id> endpoint: {e}")
        return jsonify({"error": str(e)}), 500  # Return error if something goes wrong

@app.route("/song", methods=["POST"])
def create_song():
    """Create a new song"""
    try:
        # Extract song data from the request body
        song_data = request.get_json()
        
        # Check if song with the given ID already exists
        if db.songs.find_one({"id": song_data["id"]}):
            return jsonify({"Message": f"song with id {song_data['id']} already present"}), 302
        
        # Insert the new song into the database
        result = db.songs.insert_one(song_data)
        
        # Return the inserted ID in the response
        return jsonify({"inserted id": str(result.inserted_id)}), 201

    except Exception as e:
        print(f"Error in /song POST endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """Update a song by its ID"""
    try:
        # Extract song data from the request body
        song_data = request.get_json()
        
        # Find the song in the database by its ID
        song = db.songs.find_one({"id": id})
        
        if song is None:
            # Return 404 if the song does not exist
            return jsonify({"message": "song not found"}), 404
        
        # Update the song with the new data
        db.songs.update_one(
            {"id": id},
            {"$set": song_data}
        )
        
        # Return the updated song data
        updated_song = db.songs.find_one({"id": id})
        
        if updated_song["lyrics"] == song_data["lyrics"] and updated_song["title"] == song_data["title"]:
            # If no changes were made, return a message indicating nothing was updated
            return jsonify({"message": "song found, but nothing updated"}), 200
        
        return jsonify(updated_song), 200

    except Exception as e:
        print(f"Error in /song/<id> PUT endpoint: {e}")
        return jsonify({"error": str(e)}), 500 

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """Delete a song by its ID"""
    try:
        # Attempt to delete the song from the database
        result = db.songs.delete_one({"id": id})
        
        if result.deleted_count == 0:
            # If no song was deleted (i.e., song not found)
            return jsonify({"message": "song not found"}), 404
        
        # If the song was successfully deleted, return a 204 No Content
        return '', 204

    except Exception as e:
        print(f"Error in /song/<id> DELETE endpoint: {e}")
        return jsonify({"error": str(e)}), 500       