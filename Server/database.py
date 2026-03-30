from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error
from common.config import Config

app = Flask(__name__)

# ====================== Database Configuration ======================
Conf = Config.get()

# Helper function to get a new database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(**Conf['SERVER'])
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

# 1. get userID by email
@app.route('/users/email', methods=['GET'])
def get_userID_by_email():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Please provide email parameter"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM User WHERE email = %s", (email,))
        user_id = cursor.fetchone() # user is a list of dictionaries
        
        if user_id:
            return jsonify({"success": True, "user": user_id})
        else:
            return jsonify({"error": "user_id not found"}), 404
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()





# 2. get email by userID
@app.route('/users/userID', methods=['GET'])
def get_email_by_userID():
    userID = request.args.get('userID')
    if not userID:
        return jsonify({"error": "Please provide userID parameter"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email FROM User WHERE user_id = %s", (userID,))
        email = cursor.fetchone() # email is a list of dictionaries
        
        if email:
            return jsonify({"success": True, "email": email})
        else:
            return jsonify({"error": "email not found"}), 404
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()



# 3. get password by email
@app.route('/users/password', methods=['GET'])
def get_password_by_email():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Please provide email parameter"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_password FROM User WHERE email = %s", (email,))
        password = cursor.fetchone() # user is a list of dictionaries
        
        if password:
            return jsonify({"success": True, "password": password})
        else:
            return jsonify({"error": "password not found"}), 404
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# 4. get message by userID_A userID_B
@app.route('/users/message', methods=['GET'])
def get_message_by_users():
    userID_A = request.args.get('userID_A')
    userID_B = request.args.get('userID_B')
    page = request.args.get("page") 
    offset = (page-1) * 10


    if not userID_A:
        return jsonify({"error": "Please provide userID_A"}), 400
    
    if not userID_B:
        return jsonify({"error": "Please provide userID_B"}), 400
    
    if not page:
        return jsonify({"error": "Please provide page"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT message, time 
        FROM Message 
        WHERE (sender = %s AND receiver = %s) 
        OR (receiver = %s AND sender = %s)
        ORDER BY time DESC 
        LIMIT 10 OFFSET %s
        """

        cursor.execute(query, (userID_A, userID_B, userID_A, userID_B, offset))

        message = cursor.fetchone() 
        
        if message:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"error": "message not found"}), 404
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)