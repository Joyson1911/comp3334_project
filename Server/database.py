"""
message table: email ->


"""
from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error
import configparser

# Create a ConfigParser object
config = configparser.ConfigParser()


app = Flask(__name__)

# ====================== Database Configuration ======================
DB_CONFIG = config.read('databaseConfig.ini') 



# Helper function to get a new database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# ====================== After Request Headers (from your previous code) ======================
@app.after_request
def add_headers(response):
    response.headers['User-Agent'] = 'comp3334/1.0'
    response.headers['Accept'] = 'application/json'
    response.headers['Content-Type'] = 'application/json'
    return response

# ====================== API Endpoints ======================

# helper method
def get_all_users():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)   # Returns rows as dict
        cursor.execute("SELECT user_id, email FROM USER")
        users = cursor.fetchall()
        
        return users
    
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 1. get userID by email
@app.route('/users/email', methods=['GET'])
def get_user_by_email():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Please provide email parameter"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, email FROM USER WHERE email = %s", (email,))
        user = cursor.fetchone() # user is a list of dictionaries
        
        if user:
            return jsonify({"success": True, "user": user})
        else:
            return jsonify({"error": "User not found"}), 404
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()





# 2. get email by userID
@app.route('/users/userID', methods=['GET'])
def get_user_by_email():
    userID = request.args.get('userID')
    if not userID:
        return jsonify({"error": "Please provide userID parameter"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, email FROM USER WHERE user_id = %s", (userID))
        user = cursor.fetchone() # user is a list of dictionaries
        
        if user:
            return jsonify({"success": True, "user": user})
        else:
            return jsonify({"error": "email not found"}), 404
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()



if __name__ == '__main__':
    app.run(debug=True, port=5000)