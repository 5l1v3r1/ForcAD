import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import asyncio
import json
from functools import wraps

from sanic import Sanic
from sanic.response import json as json_response, html
import storage
from aioredis.pubsub import Receiver

import socketio

sio = socketio.AsyncServer(async_mode='sanic')
app = Sanic()
sio.attach(app)


def cors_allow_all(func):
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        response = await func(request, *args, **kwargs)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    return wrapper


@app.listener('before_server_start')
async def before_server_start(_sanic, loop):
    mpsc = Receiver(loop=loop)
    redis = await storage.get_async_redis_pool(loop)
    await redis.subscribe(
        mpsc.channel('scoreboard'),
        mpsc.channel('stolen_flags'),
    )
    sio.start_background_task(background_task, mpsc)


async def background_task(mpsc):
    async for channel, msg in mpsc.iter():
        try:
            message = msg.decode()
        except AttributeError:
            pass
        else:
            print(message, channel, channel.name)
            if channel.name == b'stolen_flags':
                print('Emitting flag stolen event')
                await sio.emit('flag_stolen', {'data': message}, namespace='/api/sio_interface')
            elif channel.name == b'scoreboard':
                print('Emitting scoreboard event')
                await sio.emit('update_scoreboard', {'data': message}, namespace='/api/sio_interface')


@sio.on('connect', namespace='/api/sio_interface')
async def handle_connect(_sid, _environ):
    loop = asyncio.get_event_loop()
    game_state = await storage.game.get_game_state_async(loop)

    teams = await storage.teams.get_teams_async(loop)
    teams = [team.to_dict() for team in teams]
    tasks = await storage.tasks.get_tasks_async(loop)
    tasks = [task.to_dict_for_participants() for task in tasks]
    if not game_state:
        state = ''
    else:
        state = game_state.to_dict()

    data_to_send = {
        'state': state,
        'teams': teams,
        'tasks': tasks,
    }

    await sio.emit(
        'init_scoreboard',
        {
            'data': json.dumps(data_to_send),
        },
        namespace='/api/sio_interface'
    )


@app.route('/api/teams/')
@cors_allow_all
async def get_teams(_request):
    teams = await storage.teams.get_teams_async(asyncio.get_event_loop())
    teams = [team.to_dict() for team in teams]
    return json_response(teams)


@app.route('/api/tasks/')
@cors_allow_all
async def get_tasks(_request):
    tasks = await storage.tasks.get_tasks_async(asyncio.get_event_loop())
    tasks = [task.to_dict_for_participants() for task in tasks]
    return json_response(tasks)


# noinspection PyUnresolvedReferences
@app.route('/api/teams/<team_id:int>/')
@cors_allow_all
async def get_team_history(_request, team_id):
    round = storage.game.get_current_round()
    teamtasks = storage.tasks.get_teamtasks_of_team_for_participants(team_id=team_id, current_round=round)
    return json_response(teamtasks)


@app.route('/api/status/')
@cors_allow_all
async def status(_request):
    return html("OK")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)