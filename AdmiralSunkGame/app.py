from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from random import choice, randint
import uuid
import redis
import pickle
from flask_socketio import SocketIO, emit

redis = redis.Redis(host="localhost", port=6379)

app = Flask(__name__)
app.secret_key = "most secret key"
socketio = SocketIO(app, async_mode=None)

squareSize = 12

def generateRandomMap():
    mapArr = [[0 for x in range(squareSize)] for y in range(squareSize)]
    
    shipSizes = [1, 1, 1, 1, 2, 2, 2, 3, 3, 4]

    for shipSize in shipSizes:
        while True:
            isHorizontal = choice([True, False])
            rowOrColIndex = randint(0, squareSize - 1)
            
            currentLine = [mapArr[rowOrColIndex][x] if isHorizontal else mapArr[x][rowOrColIndex] for x in range(squareSize)]
            prevLine = [0] * squareSize
            nextLine = [0] * squareSize

            if rowOrColIndex != 0:
                prevLine = [mapArr[rowOrColIndex - 1][x] if isHorizontal else mapArr[x][rowOrColIndex - 1] for x in range(squareSize)]

            if rowOrColIndex != squareSize - 1:
                nextLine = [mapArr[rowOrColIndex + 1][x] if isHorizontal else mapArr[x][rowOrColIndex + 1] for x in range(squareSize)]

            line = [0 if currentLine[x] == 0 and prevLine[x] == 0 and nextLine[x] == 0 else 1 for x in range(squareSize)]

            availableIndexes = []
            for x in range(squareSize):
                if squareSize - x < shipSize:
                    continue

                if x != 0 and 1 in line[x - 1: x + shipSize + 1]:
                    continue

                if x == 0 and 1 in line[x: x + shipSize + 1]:
                    continue

                availableIndexes.append(x)

            if not availableIndexes:
                continue

            selectedIndex = choice(availableIndexes)

            for x in range(shipSize):
                if isHorizontal:
                    mapArr[rowOrColIndex][selectedIndex + x] = 1
                else:
                    mapArr[selectedIndex + x][rowOrColIndex] = 1

            break

    return mapArr


@app.route('/')
def index():
    myId = session.get("id")

    if not myId:
        myId = str(uuid.uuid4())
        session["id"] = myId

    return render_template('index.html', id=myId)

@app.route("/match", methods=["GET", "POST"])
def match():
    if request.method == "POST":
        position = request.form.getlist("position[]")
        row, col = map(int, position)

        opponentMap = pickle.loads(redis.get(session["opponentId"]))

        opponentSocketId = redis.get(f"{session['opponentId']}-socketId").decode("UTF-8")

        socketio.emit("fired", [row, col], room=opponentSocketId)

        if opponentMap[row][col] == 1:
            return jsonify(True)
        
        return jsonify(False)

    myId = session["id"]
    myMap = generateRandomMap()
    redis.set(myId, pickle.dumps(myMap))
    
    return render_template("match.html", data=myMap)

@socketio.on('connect')
def handle_connect():
    redis.set(f"{session['id']}-socketId", request.sid)

@app.route('/invite/<opponentId>')
def start_game(opponentId):
    sessionId = session.get("id")

    if not sessionId:
        sessionId = str(uuid.uuid4())
        session["id"] = sessionId

    session["opponentId"] = opponentId
    opponentSocketId = redis.get(f"{opponentId}-socketId").decode("UTF-8")

    socketio.emit("invite-accepted", sessionId, room=opponentSocketId)
    
    return redirect(url_for("match"))

@app.route('/set_opponent', methods=["POST"])
def set_opponent():
    session["opponentId"] = request.form.get("opponentId")
    return redirect(url_for('index'))

if __name__ == '__main__':
    socketio.run(app)